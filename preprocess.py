import pandas as pd
import numpy as np
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from sklearn.preprocessing import MinMaxScaler

INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "CQzMbguNaT7uQO5vvLBe7A6i0mtLWOs09Hszc8vhQGPfDhwTBiGNL6BV30a3n2bzaBMXlBDSkZZB_TkmatBQtw=="
INFLUX_ORG = "iot_lab"

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)

print("[*] Đang đọc dữ liệu thô từ InfluxDB trong 30 phút gần nhất...")
query = '''
from(bucket: "sensor_raw")
  |> range(start: -30m)
  |> filter(fn: (r) => r._measurement == "environment")
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
'''
df = client.query_api().query_data_frame(query)

if df is None or (isinstance(df, list) and len(df) == 0) or (isinstance(df, pd.DataFrame) and df.empty):
    print("[!] Chưa có đủ dữ liệu thô trong InfluxDB! Hãy chắc chắn collector đang lưu dữ liệu.")
    exit()

if isinstance(df, list):
    df = pd.concat(df)

# Lọc các cột cần dùng
df['_time'] = pd.to_datetime(df['_time'])
df.set_index('_time', inplace=True)

# Ép kiểu dữ liệu số an toàn
num_cols = ['temperature', 'humidity', 'light']
for col in num_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# 1. Xử lý giá trị thiếu (Chỉ nội suy trên các cột số)
df[num_cols] = df[num_cols].interpolate(method='time')

# 2. Phát hiện và xử lý Outlier bằng IQR (Interquartile Range)
Q1 = df['temperature'].quantile(0.25)
Q3 = df['temperature'].quantile(0.75)
IQR = Q3 - Q1
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

# Thay outlier bằng cận trên/dưới (Clipping)
df['temp_clean'] = df['temperature'].clip(lower=lower_bound, upper=upper_bound)
num_outliers = (df['temperature'] != df['temp_clean']).sum()
print(f"[*] Đã phát hiện và làm sạch {num_outliers} điểm dị biệt (outlier) bằng phương pháp IQR.")

# 3. Resampling theo cửa sổ thời gian (Gộp trung bình mỗi 10 giây)
resampled_df = df[['temp_clean', 'humidity', 'light']].resample('10s').mean().dropna()

# 4. Tạo đặc trưng (Feature Engineering)
# Rolling Mean (trung bình trượt 3 chu kỳ)
resampled_df['temp_rolling_mean'] = resampled_df['temp_clean'].rolling(window=3).mean().fillna(resampled_df['temp_clean'])
# Delta (độ chênh lệch nhiệt độ)
resampled_df['temp_delta'] = resampled_df['temp_clean'].diff().fillna(0.0)

# Chuẩn hóa Min-Max Scaling [0, 1] cho nhiệt độ
scaler = MinMaxScaler()
resampled_df['temp_scaled'] = scaler.fit_transform(resampled_df[['temp_clean']])

# 5. Lưu kết quả tiền xử lý vào bucket "sensor_processed"
write_api = client.write_api(write_options=SYNCHRONOUS)
for timestamp, row in resampled_df.iterrows():
    p = (
        Point("environment_processed")
        .tag("device_id", "esp32_node_01")
        .field("temp_clean", float(row['temp_clean']))
        .field("temp_rolling_mean", float(row['temp_rolling_mean']))
        .field("temp_delta", float(row['temp_delta']))
        .field("temp_scaled", float(row['temp_scaled']))
        .field("humidity", float(row['humidity']))
        .time(int(timestamp.value), WritePrecision.NS)
    )
    write_api.write(bucket="sensor_processed", record=p)

print("[✓] Tiền xử lý thành công và đã ghi vào bucket 'sensor_processed'!")
print(resampled_df.tail(3))