#include <WiFi.h>
#include <PubSubClient.h>
#include <DHTesp.h>

const char* WIFI_SSID = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";

// Đổi sang Broker công cộng để máy tính bắt được trực tiếp
const char* MQTT_SERVER = "broker.hivemq.com";
const int MQTT_PORT = 1883;
const char* MQTT_TOPIC = "iot/lab2/esp32_sensor";

const int DHT_PIN = 15;
const int TRIG_PIN = 5;
const int ECHO_PIN = 18;
const int LED_PIN = 2;
const unsigned long SEND_INTERVAL_MS = 2000; // Phát mỗi 2 giây

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
DHTesp dht;
unsigned long lastSend = 0;
unsigned long sequenceNo = 0;

void connectWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD, 6);
  Serial.print("Connecting WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(" connected");
}

void connectMQTT() {
  while (!mqttClient.connected()) {
    String clientId = "ESP32-Wokwi-" + String((uint32_t)ESP.getEfuseMac(), HEX);
    Serial.print("Connecting MQTT...");
    // HiveMQ public không cần token/password
    if (mqttClient.connect(clientId.c_str())) {
      Serial.println(" connected to HiveMQ!");
    } else {
      Serial.printf(" failed, rc=%d. Retry in 2 s\n", mqttClient.state());
      delay(2000);
    }
  }
}

float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duration == 0) return NAN;
  return duration * 0.0343f / 2.0f;
}

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  dht.setup(DHT_PIN, DHTesp::DHT22);
  connectWiFi();
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setBufferSize(512);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWiFi();
  if (!mqttClient.connected()) connectMQTT();
  mqttClient.loop();

  unsigned long now = millis();
  if (now - lastSend < SEND_INTERVAL_MS) return;
  lastSend = now;

  TempAndHumidity data = dht.getTempAndHumidity();
  float distance = readDistanceCm();

  if (!isfinite(data.temperature) || !isfinite(data.humidity) || !isfinite(distance)) {
    Serial.println("Invalid sensor data - skip publish");
    return;
  }

  sequenceNo++;
  char payload[300];
  // Format JSON chuẩn bài thực hành 2
  snprintf(payload, sizeof(payload),
    "{\"device_id\":\"esp32_wokwi\",\"location\":\"lab_room_302\","
    "\"temperature\":%.2f,\"humidity\":%.2f,\"distance_cm\":%.2f,\"light\":%d,"
    "\"sequence\":%lu,\"uptime_s\":%lu}",
    data.temperature, data.humidity, distance, 350,
    sequenceNo, millis() / 1000);

  bool ok = mqttClient.publish(MQTT_TOPIC, payload);
  Serial.printf("%s | publish=%s\n", payload, ok ? "OK" : "FAILED");

  digitalWrite(LED_PIN, HIGH);
  delay(80);
  digitalWrite(LED_PIN, LOW);
}