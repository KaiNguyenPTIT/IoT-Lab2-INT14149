import json
import time
import random
import paho.mqtt.client as mqtt

BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "iot/lab2/esp32_sensor"

try:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
except AttributeError:
    client = mqtt.Client()

client.connect(BROKER, PORT, 60)
print(f"[*] Sensor Node đang phát dữ liệu lên topic: {TOPIC}")

while True:
    now = time.time()
    # Sinh dữ liệu cảm biến
    temp = round(random.uniform(26.0, 31.0), 2)
    hum = round(random.uniform(60.0, 80.0), 2)
    light = random.randint(200, 800)

    # Thỉnh thoảng tạo 1 điểm dị biệt (Outlier) để kiểm thử tiền xử lý
    if random.random() < 0.08:
        temp = 85.5  # Nhiệt độ đột biến bất thường

    payload = {
        "device_id": "esp32_node_01",
        "location": "lab_room_302",
        "timestamp": now,
        "temperature": temp,
        "humidity": hum,
        "light": light
    }

    client.publish(TOPIC, json.dumps(payload))
    print(f"[GỬI] Temp: {temp}°C | Hum: {hum}% | Light: {light} lux")
    time.sleep(2)  # Chu kỳ phát 2 giây/lần