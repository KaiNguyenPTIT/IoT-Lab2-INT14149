# 📡 BÀI THỰC HÀNH SỐ 2: THU THẬP, LƯU TRỮ VÀ TIỀN XỬ LÝ DỮ LIỆU IoT

> **Học phần:** IoT và Ứng dụng (INT14149)  
> **Sinh viên thực hiện:** Nguyễn Đình Khải 
> **Mã sinh viên:** B23DCCN420

---

## 📖 1. Giới thiệu tổng quan
Dự án xây dựng một hệ thống pipeline thu thập, lưu trữ theo chuỗi thời gian (time-series) và tiền xử lý dữ liệu IoT hoàn chỉnh:
- **Tầng biên (Edge/Sensor):** Vi điều khiển ESP32 đọc dữ liệu từ cảm biến nhiệt độ/độ ẩm (DHT22) và cảm biến khoảng cách (HC-SR04) mô phỏng trên nền tảng Wokwi.
- **Tầng truyền thông (Protocol):** Giao thức MQTT qua Public Broker (`broker.hivemq.com`), QoS = 0/1.
- **Tầng lưu trữ (Time-Series DB):** InfluxDB v2.x tối ưu hóa lưu trữ dữ liệu cảm biến theo thời gian thực với chính sách lưu trữ (Retention Policy).
- **Tầng tiền xử lý (Preprocessing):** Xử lý dữ liệu thiếu (Interpolation), loại bỏ nhiễu dị biệt (Outlier Detection qua IQR), Resampling, làm mịn tín hiệu (Rolling Mean), tính toán độ biến thiên (Delta) và chuẩn hóa dữ liệu (MinMax Scaling).
- **Tầng hiển thị (Dashboard):** Web Dashboard tương tác thời gian thực xây dựng bằng Flask và Chart.js.

---

## 📁 2. Cấu trúc thư mục mã nguồn

```text
├── firmware.ino        # Mã nguồn nhúng C++ cho ESP32 chạy trên Wokwi (DHT22 + HC-SR04)
├── sensor_node.py      # Script Python giả lập node cảm biến phát dữ liệu MQTT (chạy thử độc lập)
├── collector.py        # Subscriber MQTT, validate gói tin, đo độ trễ và ghi vào InfluxDB (sensor_raw)
├── preprocess.py       # Pipeline tiền xử lý: Nội suy, Lọc Outlier IQR, Resampling, Feature Engineering
├── dashboard.py        # Ứng dụng Web Dashboard trực quan hóa dữ liệu Real-time và Processed
├── config.py           # File cấu hình tập trung (MQTT Broker, InfluxDB Token, Org, Buckets)
└── README.md           # Tài liệu hướng dẫn cài đặt và vận hành hệ thống
```

---

## 🗄️ 3. Thiết kế Schema Cơ sở dữ liệu (InfluxDB v2)

Hệ thống thiết kế tách biệt 2 Bucket dữ liệu:

### 3.1. Bucket `sensor_raw` (Dữ liệu thô - Retention: 7 ngày)
- **Measurement:** `environment`
- **Tag Set (Indexed):**
  - `device_id`: Định danh thiết bị (ví dụ: `esp32_wokwi`).
  - `location`: Vị trí đặt cảm biến (`lab_room_302`).
- **Field Set:**
  - `temperature` (Float): Nhiệt độ đo đạc (°C).
  - `humidity` (Float): Độ ẩm không khí (%).
  - `distance_cm` (Float): Khoảng cách cảm biến siêu âm (cm).
  - `latency_ms` (Float): Độ trễ truyền nhận gói tin end-to-end (ms).

### 3.2. Bucket `sensor_processed` (Dữ liệu đã tiền xử lý)
- **Measurement:** `environment_processed`
- **Tag Set:** `device_id`
- **Field Set:**
  - `temp_clean` (Float): Nhiệt độ sau khi làm sạch ngoại lai (IQR clipping).
  - `temp_rolling_mean` (Float): Nhiệt độ làm mịn bằng trượt trung bình cửa sổ 3 mẫu.
  - `temp_delta` (Float): Biến thiên nhiệt độ so với chu kỳ trước.
  - `temp_scaled` (Float): Dữ liệu nhiệt độ chuẩn hóa miền [0, 1].
  - `humidity` (Float): Độ ẩm sau khi resampling theo chu kỳ 10 giây.

---

## 🚀 4. Hướng dẫn cài đặt và chạy hệ thống

### Bước 1: Chuẩn bị môi trường Python
Yêu cầu Python 3.10 trở lên. Cài đặt các thư viện cần thiết:
```bash
pip install paho-mqtt influxdb-client pandas numpy scikit-learn flask
```

### Bước 2: Khởi động InfluxDB
- Chạy binary InfluxDB cục bộ:
  ```cmd
  influxd.exe
  ```
- Truy cập trình duyệt tại `http://localhost:8086`, tạo Org `iot_lab`, tạo 2 Bucket: `sensor_raw` và `sensor_processed`.
- Tạo All-Access API Token và cập nhật vào file `config.py` (hoặc trực tiếp trong các file script).

### Bước 3: Chạy thiết bị cảm biến (Chọn 1 trong 2 cách)
- **Cách 1 (Wokwi):** Mở dự án ESP32 trên Wokwi, dán code từ `firmware.ino` và bấm **Play Simulation**.
- **Cách 2 (Python Simulator):** Chạy node cảm biến giả lập bằng lệnh:
  ```bash
  python sensor_node.py
  ```

### Bước 4: Thu thập và lưu trữ dữ liệu vào InfluxDB
Mở một terminal mới và chạy service Collector:
```bash
python collector.py
```
*Chương trình sẽ lắng nghe tin nhắn MQTT, kiểm tra tính hợp lệ và ghi các Point vào InfluxDB.*

### Bước 5: Chạy tiến trình tiền xử lý dữ liệu
Sau khi hệ thống thu thập được một lượng dữ liệu (khoảng 1–2 phút), chạy script xử lý:
```bash
python preprocess.py
```
*Kết quả tiền xử lý sẽ được tính toán và lưu tự động vào bucket `sensor_processed`.*

### Bước 6: Khởi chạy Web Dashboard giám sát
Khởi chạy giao diện giám sát:
```bash
python dashboard.py
```
Mở trình duyệt truy cập: **`http://localhost:5000`** để theo dõi biểu đồ dữ liệu thời gian thực, độ trễ và bảng số liệu tiền xử lý.

---

## 📊 5. Thuật toán tiền xử lý áp dụng
1. **Linear Interpolation:** Tự động bù đắp dữ liệu bị khuyết thiếu dựa trên mốc thời gian liền kề.
2. **IQR Outlier Filtering:** 
   - Tính $IQR = Q_3 - Q_1$.
   - Giới hạn hợp lệ trong khoảng $[Q_1 - 1.5 \times IQR, Q_3 + 1.5 \times IQR]$.
   - Loại bỏ và cắt gọt các điểm nhiễu cảm biến bất thường (như xung nhiệt độ cao đột biến).
3. **Resampling:** Gộp trung bình theo khung thời gian cố định 10 giây để đồng nhất nhịp lấy mẫu.
4. **Feature Engineering & Normalization:**
   - **Rolling Mean:** Cửa sổ trượt 3 bước để giảm dao động tức thời.
   - **Delta ($\Delta$):** Đo đạo hàm bậc nhất của chuỗi nhiệt độ.
   - **MinMaxScaler:** Co dãn miền giá trị về thang $[0, 1]$.
```

