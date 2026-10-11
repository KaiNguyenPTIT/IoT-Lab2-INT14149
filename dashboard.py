from flask import Flask, jsonify, render_template_string
from influxdb_client import InfluxDBClient
import pandas as pd

app = Flask(__name__)

INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "CQzMbguNaT7uQO5vvLBe7A6i0mtLWOs09Hszc8vhQGPfDhwTBiGNL6BV30a3n2bzaBMXlBDSkZZB_TkmatBQtw=="
INFLUX_ORG = "iot_lab"

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>IoT Realtime Dashboard - INT14149</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f4f6f9; margin: 20px; color: #333; }
        .header { background: #1e3a8a; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .header h1 { margin: 0 0 8px 0; font-size: 24px; }
        .header p { margin: 0; opacity: 0.85; font-size: 14px; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); margin-bottom: 20px; }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }
        .metric-box { background: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.08); border-left: 5px solid #2563eb; }
        .metric-title { font-size: 13px; color: #6b7280; font-weight: bold; text-transform: uppercase; }
        .metric-val { font-size: 26px; font-weight: bold; color: #1e3a8a; margin-top: 5px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
        th, td { border: 1px solid #e5e7eb; padding: 8px 12px; text-align: center; }
        th { background: #f9fafb; font-weight: 600; color: #374151; }
        tr:nth-child(even) { background: #fdfdfd; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 HỆ THỐNG GIÁM SÁT VÀ TIỀN XỬ LÝ DỮ LIỆU IoT</h1>
        <p>Học phần: IoT và Ứng dụng (INT14149) | Thiết bị: ESP32 (Wokwi) | Time-Series DB: InfluxDB v2</p>
    </div>

    <!-- KHỐI METRIC TỨC THỜI -->
    <div class="grid-4">
        <div class="metric-box" style="border-left-color: #ef4444;">
            <div class="metric-title">Nhiệt độ thô</div>
            <div class="metric-val" id="valTemp">-- °C</div>
        </div>
        <div class="metric-box" style="border-left-color: #3b82f6;">
            <div class="metric-title">Độ ẩm</div>
            <div class="metric-val" id="valHum">-- %</div>
        </div>
        <div class="metric-box" style="border-left-color: #10b981;">
            <div class="metric-title">Khoảng cách (Wokwi)</div>
            <div class="metric-val" id="valDist">-- cm</div>
        </div>
        <div class="metric-box" style="border-left-color: #f59e0b;">
            <div class="metric-title">Độ trễ End-to-End TB</div>
            <div class="metric-val" id="valLat">-- ms</div>
        </div>
    </div>

    <!-- HÀNG BIỂU ĐỒ 1: REAL-TIME -->
    <div class="grid-2">
        <div class="card">
            <h3>📈 1. Dữ liệu thô Real-Time (Cảm biến)</h3>
            <canvas id="rawChart"></canvas>
        </div>
        <div class="card">
            <h3>⚡ 2. Độ trễ End-to-End theo thời gian (ms)</h3>
            <canvas id="latChart"></canvas>
        </div>
    </div>

    <!-- HÀNG BIỂU ĐỒ 2: ĐÃ XỬ LÝ -->
    <div class="grid-2">
        <div class="card">
            <h3>🧹 3. Lọc Outlier IQR & Làm mịn (Rolling Mean)</h3>
            <canvas id="procChart"></canvas>
        </div>
        <div class="card">
            <h3>📐 4. Tạo đặc trưng (Delta) & Chuẩn hóa (MinMax)</h3>
            <canvas id="featureChart"></canvas>
        </div>
    </div>

    <!-- BẢNG SỐ LIỆU ĐỂ BÁO CÁO -->
    <div class="card">
        <h3>📋 Bảng số liệu tiền xử lý gần nhất (Dùng cho Báo cáo thực nghiệm)</h3>
        <table>
            <thead>
                <tr>
                    <th>Thời gian</th>
                    <th>Nhiệt độ sạch (°C)</th>
                    <th>Rolling Mean (°C)</th>
                    <th>Biến thiên (Delta)</th>
                    <th>Chuẩn hóa [0, 1]</th>
                    <th>Độ ẩm (%)</th>
                </tr>
            </thead>
            <tbody id="tableBody">
                <tr><td colspan="6">Đang tải dữ liệu...</td></tr>
            </tbody>
        </table>
    </div>

    <script>
        const ctxRaw = document.getElementById('rawChart').getContext('2d');
        const ctxLat = document.getElementById('latChart').getContext('2d');
        const ctxProc = document.getElementById('procChart').getContext('2d');
        const ctxFeat = document.getElementById('featureChart').getContext('2d');

        let rawChart = new Chart(ctxRaw, {
            type: 'line',
            data: { labels: [], datasets: [
                { label: 'Nhiệt độ (°C)', data: [], borderColor: '#ef4444', tension: 0.2 },
                { label: 'Độ ẩm (%)', data: [], borderColor: '#3b82f6', tension: 0.2 },
                { label: 'Khoảng cách (cm)', data: [], borderColor: '#10b981', tension: 0.2 }
            ]}
        });

        let latChart = new Chart(ctxLat, {
            type: 'line',
            data: { labels: [], datasets: [
                { label: 'Độ trễ (ms)', data: [], borderColor: '#f59e0b', backgroundColor: 'rgba(245, 158, 11, 0.1)', fill: true }
            ]}
        });

        let procChart = new Chart(ctxProc, {
            type: 'line',
            data: { labels: [], datasets: [
                { label: 'Nhiệt độ sạch (IQR)', data: [], borderColor: '#f97316', tension: 0.1 },
                { label: 'Rolling Mean (Cửa sổ 3)', data: [], borderColor: '#8b5cf6', borderWidth: 2, tension: 0.3 }
            ]}
        });

        let featChart = new Chart(ctxFeat, {
            type: 'line',
            data: { labels: [], datasets: [
                { label: 'Chuẩn hóa MinMax [0-1]', data: [], borderColor: '#06b6d4', yAxisID: 'y' },
                { label: 'Biến thiên Delta (°C)', data: [], borderColor: '#ec4899', yAxisID: 'y1', borderDash: [5, 5] }
            ]},
            options: {
                scales: {
                    y: { type: 'linear', position: 'left', min: 0, max: 1 },
                    y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false } }
                }
            }
        });

        function updateData() {
            fetch('/api/data').then(res => res.json()).then(d => {
                // Cập nhật Metrics
                if (d.latest) {
                    document.getElementById('valTemp').innerText = d.latest.temperature + ' °C';
                    document.getElementById('valHum').innerText = d.latest.humidity + ' %';
                    document.getElementById('valDist').innerText = (d.latest.distance_cm || 0) + ' cm';
                    document.getElementById('valLat').innerText = (d.avg_latency || 0) + ' ms';
                }

                // Cập nhật Chart Realtime
                if (d.raw_times.length > 0) {
                    rawChart.data.labels = d.raw_times;
                    rawChart.data.datasets[0].data = d.raw_temp;
                    rawChart.data.datasets[1].data = d.raw_hum;
                    rawChart.data.datasets[2].data = d.raw_dist;
                    rawChart.update();

                    latChart.data.labels = d.raw_times;
                    latChart.data.datasets[0].data = d.raw_lat;
                    latChart.update();
                }

                // Cập nhật Chart Processed
                if (d.proc_times.length > 0) {
                    procChart.data.labels = d.proc_times;
                    procChart.data.datasets[0].data = d.proc_temp_clean;
                    procChart.data.datasets[1].data = d.proc_rolling;
                    procChart.update();

                    featChart.data.labels = d.proc_times;
                    featChart.data.datasets[0].data = d.proc_scaled;
                    featChart.data.datasets[1].data = d.proc_delta;
                    featChart.update();

                    // Cập nhật Bảng số liệu
                    let rowsHtml = '';
                    for (let i = d.table_rows.length - 1; i >= 0; i--) {
                        let r = d.table_rows[i];
                        rowsHtml += `<tr>
                            <td>${r.time}</td>
                            <td>${r.clean.toFixed(2)}</td>
                            <td>${r.rolling.toFixed(2)}</td>
                            <td>${r.delta.toFixed(2)}</td>
                            <td>${r.scaled.toFixed(3)}</td>
                            <td>${r.hum.toFixed(1)}</td>
                        </tr>`;
                    }
                    document.getElementById('tableBody').innerHTML = rowsHtml;
                }
            });
        }

        setInterval(updateData, 3000);
        updateData();
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_PAGE)


@app.route('/api/data')
def get_data():
    q_raw = '''
    from(bucket: "sensor_raw")
      |> range(start: -15m)
      |> filter(fn: (r) => r._measurement == "environment")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    q_proc = '''
    from(bucket: "sensor_processed")
      |> range(start: -15m)
      |> filter(fn: (r) => r._measurement == "environment_processed")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''

    raw_df = client.query_api().query_data_frame(q_raw)
    proc_df = client.query_api().query_data_frame(q_proc)

    data = {
        "raw_times": [], "raw_temp": [], "raw_hum": [], "raw_dist": [], "raw_lat": [],
        "proc_times": [], "proc_temp_clean": [], "proc_rolling": [], "proc_delta": [], "proc_scaled": [],
        "table_rows": [], "latest": None, "avg_latency": 0
    }

    if raw_df is not None and not (isinstance(raw_df, list) and len(raw_df) == 0) and not (
            isinstance(raw_df, pd.DataFrame) and raw_df.empty):
        if isinstance(raw_df, list): raw_df = pd.concat(raw_df)
        raw_df['_time'] = pd.to_datetime(raw_df['_time']).dt.strftime('%H:%M:%S')
        tail_raw = raw_df.tail(20)
        data["raw_times"] = tail_raw['_time'].tolist()
        data["raw_temp"] = tail_raw['temperature'].tolist()
        data["raw_hum"] = tail_raw['humidity'].tolist()
        data["raw_dist"] = tail_raw.get('distance_cm', pd.Series([0] * len(tail_raw))).fillna(0).tolist()
        data["raw_lat"] = tail_raw.get('latency_ms', pd.Series([0] * len(tail_raw))).fillna(0).tolist()

        last = raw_df.iloc[-1]
        data["latest"] = {
            "temperature": float(last['temperature']),
            "humidity": float(last['humidity']),
            "distance_cm": float(last.get('distance_cm', 0))
        }
        data["avg_latency"] = round(float(raw_df['latency_ms'].mean()), 1) if 'latency_ms' in raw_df else 0

    if proc_df is not None and not (isinstance(proc_df, list) and len(proc_df) == 0) and not (
            isinstance(proc_df, pd.DataFrame) and proc_df.empty):
        if isinstance(proc_df, list): proc_df = pd.concat(proc_df)
        proc_df['_time'] = pd.to_datetime(proc_df['_time']).dt.strftime('%H:%M:%S')
        tail_proc = proc_df.tail(20)
        data["proc_times"] = tail_proc['_time'].tolist()
        data["proc_temp_clean"] = tail_proc['temp_clean'].tolist()
        data["proc_rolling"] = tail_proc['temp_rolling_mean'].tolist()
        data["proc_delta"] = tail_proc['temp_delta'].tolist()
        data["proc_scaled"] = tail_proc['temp_scaled'].tolist()

        # Tạo bảng 5 dòng gần nhất
        for _, r in proc_df.tail(5).iterrows():
            data["table_rows"].append({
                "time": r['_time'],
                "clean": float(r['temp_clean']),
                "rolling": float(r['temp_rolling_mean']),
                "delta": float(r['temp_delta']),
                "scaled": float(r['temp_scaled']),
                "hum": float(r['humidity'])
            })

    return jsonify(data)


if __name__ == '__main__':
    print("[*] Dashboard đang chạy tại: http://localhost:5000")
    app.run(port=5000, debug=False)