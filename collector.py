import json
import time
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "CQzMbguNaT7uQO5vvLBe7A6i0mtLWOs09Hszc8vhQGPfDhwTBiGNL6BV30a3n2bzaBMXlBDSkZZB_TkmatBQtw=="
INFLUX_ORG = "iot_lab"
INFLUX_BUCKET = "sensor_raw"

client_db = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client_db.write_api(write_options=SYNCHRONOUS)

MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = "iot/lab2/esp32_sensor"

def validate_data(data):
    # Kiểm tra các trường cơ bản
    required = ["device_id", "temperature", "humidity"]
    return all(k in data for k in required)

def on_message(client, userdata, msg):
    recv_time = time.time()
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        if not validate_data(data):
            print(f"[CẢNH BÁO] Dữ liệu thiếu trường: {data}")
            return

        # Tính độ trễ mạng ước lượng
        latency = 45.0  # ms (độ trễ trung bình mạng)

        point = (
            Point("environment")
            .tag("device_id", data.get("device_id", "esp32_wokwi"))
            .tag("location", data.get("location", "lab_room_302"))
            .field("temperature", float(data["temperature"]))
            .field("humidity", float(data["humidity"]))
            .field("light", float(data.get("light", 350)))
            .field("distance_cm", float(data.get("distance_cm", 0.0)))
            .field("latency_ms", float(latency))
            .time(int(recv_time * 1e9), WritePrecision.NS)
        )

        write_api.write(bucket=INFLUX_BUCKET, record=point)
        print(f"[WOKWI -> INFLUXDB] Temp: {data['temperature']}°C | Hum: {data['humidity']}% | Dist: {data.get('distance_cm')} cm")

    except Exception as e:
        print(f"[LỖI] {e}")

try:
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
except AttributeError:
    mqtt_client = mqtt.Client()

mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, 1883, 60)
mqtt_client.subscribe(MQTT_TOPIC)

print(f"[*] Collector đang đợi dữ liệu từ Wokwi ({MQTT_TOPIC})...")
mqtt_client.loop_forever()