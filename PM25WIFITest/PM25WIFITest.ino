#include <ArduinoJson.h>
#include <ArduinoJson.hpp>
#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include "Adafruit_PM25AQI.h"


Adafruit_PM25AQI aqi = Adafruit_PM25AQI();

const char* ssid = "";
const char* password = "";
const char* mqtt_server = "10.0.0.94";

WiFiClient espClient;
PubSubClient client(espClient);
unsigned long lastMsg = 0;
#define MSG_BUFFER_SIZE (50)
char msg[MSG_BUFFER_SIZE];
int value = 0;

void setup_wifi() {

  delay(100);
  // We start by connecting to a WiFi network
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  //  WiFi.init(AP_STA_MODE);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  randomSeed(micros());

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void callback(char* topic, byte* payload, unsigned int length) {
}

void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Create a random client ID
    String clientId = "ESP8266Client-";
    clientId += String(random(0xffff), HEX);
    // Attempt to connect
    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
      // Once connected, publish an announcement...
      client.publish("outTopic", "hello world");
      // ... and resubscribe
      client.subscribe("inTopic");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  while (!Serial);
  Serial.println("Adafruit PMSA003I Air Quality Sensor MQTT Test");
  delay(1000);
  if (!aqi.begin_I2C()) {  // connect to the sensor over I2C
    Serial.println("Could not find PM 2.5 sensor!");
    while (1) delay(10);
  }

  Serial.println("PM25 found!");

  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

void loop() {
  PM25_AQI_Data data;

  if (!aqi.read(&data)) {
    Serial.println("Could not read from AQI");
    delay(500);  // try again in a bit!
    return;
  }
  

  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  StaticJsonDocument<32> doc;
  char output[55];

  long now = millis();
  if (now - lastMsg > 5000) {
    lastMsg = now;
    Serial.println("AQI reading success");
    float pm10 = data.pm10_env;
    float pm25 = data.pm25_env;
    float pm100 = data.pm100_env;
    doc["pm10"] = pm10;
    doc["pm25"] = pm25;
    doc["pm100"] = pm100;

    Serial.println("Read");

    serializeJson(doc, output);
    Serial.println(output);
    client.publish("/home/aqm_data", output);
    Serial.println("Sent");
  }
}
