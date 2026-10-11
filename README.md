\# BÀI THỰC HÀNH SỐ 2: THU THẬP, LƯU TRỮ VÀ TIỀN XỬ LÝ DỮ LIỆU IoT

\- \*\*Học phần\*\*: IoT và Ứng dụng (INT14149)

\- \*\*Thiết bị\*\*: ESP32 (Wokwi simulation) kết nối DHT22, HC-SR04

\- \*\*Database\*\*: InfluxDB 2.7.11 (Time-Series Database)

\- \*\*Giao thức\*\*: MQTT (HiveMQ Broker)

\- \*\*Giao diện\*\*: Web Dashboard (Flask + Chart.js)



\---



\## 1. Cấu trúc thư mục

\- `firmware.ino`: Mã nguồn nhúng ESP32 trên Wokwi, đọc cảm biến và publish JSON lên MQTT.

\- `collector.py`: Client Python nhận dữ liệu MQTT, validate và lưu vào InfluxDB thô (`sensor\_raw`).

\- `preprocess.py`: Kéo dữ liệu, xử lý missing value, lọc Outlier IQR, resampling và chuẩn hóa Min-Max.

\- `dashboard.py`: Ứng dụng Web hiển thị dữ liệu real-time, độ trễ và số liệu tiền xử lý.

\- `config.py`: File cấu hình chung cho hệ thống.



\---



\## 2. Hướng dẫn chạy hệ thống



\### Bước 1: Khởi động InfluxDB

Chạy `influxd.exe` tại cổng `http://localhost:8086` (tạo 2 bucket: `sensor\_raw` và `sensor\_processed`).



\### Bước 2: Cài đặt thư viện Python

```bash

pip install paho-mqtt influxdb-client pandas numpy scikit-learn flask

