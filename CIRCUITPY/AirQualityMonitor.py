import ssl
import socketpool
import wifi
import json
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import adafruit_bme680
import time
import board
import adafruit_sgp30
from adafruit_pm25.i2c import PM25_I2C
from adafruit_lc709203f import LC709203F

# w = microcontroller.watchdog
# w.timeout = 60
# w.mode = watchdog.WatchDogMode.RESET

# Initializing variables and I2C devices
i2c = board.STEMMA_I2C()
reset_pin = None
pm25 = PM25_I2C(i2c, reset_pin)
aqdata = {}
sgp30 = adafruit_sgp30.Adafruit_SGP30(i2c)
bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c, address=0x76)
# This offset can be adjusted according to a known good temperature to ensure the BME680 reads accurately.
temperature_offset = -3.21
bme680.sea_level_pressure = 1013.25
# These baseline numbers were gathered by calibrating the sensor for 12 hours. 
# The baseline stays valid for 7 days while powered off
sgp30.set_iaq_baseline(39644, 41725)
# The SGP30 uses temperature and humidity data to calculate eCO2 and TVOC, so the readings from the BME680 are used
sgp30.set_iaq_relative_humidity(
    celsius=bme680.temperature + temperature_offset,
    relative_humidity=bme680.relative_humidity
    )
vsensor = LC709203F(i2c)

print("Battery: %0.3f Volts / %0.1f %%" % (vsensor.cell_voltage, vsensor.cell_percent))

# Add a secrets.py to your filesystem that has a dictionary called secrets with "ssid" and
# "password" keys with your WiFi credentials. DO NOT share that file or commit it into 
# Git or other source control.

bme680.temperature_oversample
bme680.humidity_oversample
bme680.pressure_oversample

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

try:
    print("Connecting to %s" % secrets["ssid"])
    wifi.radio.connect(secrets["ssid"], secrets["password"])
    print("Connected to %s!" % secrets["ssid"])
except ConnectionError:
    print("Unable to connect to %s" % secrets["ssid"])


### Topic Setup ###

# MQTT Topic
mqtt_topic = "/home/aqm"

### Code ###
# Define callback methods which are called when events occur
# pylint: disable=unused-argument, redefined-outer-name
def connect(mqtt_client, userdata, flags, rc):
    # This function will be called when the mqtt_client is connected
    # successfully to the broker.
    print("Connected to MQTT Broker!")
    print("Flags: {0}\n RC: {1}".format(flags, rc))

def disconnect(mqtt_client, userdata, rc):
    # This method is called when the mqtt_client disconnects
    # from the broker.
    print("Disconnected from MQTT Broker!")

def subscribe(mqtt_client, userdata, topic, granted_qos):
    # This method is called when the mqtt_client subscribes to a new feed.
    print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))

def unsubscribe(mqtt_client, userdata, topic, pid):
    # This method is called when the mqtt_client unsubscribes from a feed.
    print("Unsubscribed from {0} with PID {1}".format(topic, pid))

def publish(mqtt_client, userdata, topic, pid):
    # This method is called when the mqtt_client publishes data to a feed.
    print("Published to {0} with PID {1}".format(topic, pid))

def message(client, topic, message):
    # Method called when a client's subscribed feed has a new value.
    print("New message on topic {0}: {1}".format(topic, message))

# Create a socket pool
pool = socketpool.SocketPool(wifi.radio)

# Set up a MiniMQTT Client
mqtt_client = MQTT.MQTT(
    broker=secrets["broker"],
    port=secrets["port"],
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)

# Connect callback handlers to mqtt_client
mqtt_client.on_connect = connect
mqtt_client.on_disconnect = disconnect
mqtt_client.on_subscribe = subscribe
mqtt_client.on_unsubscribe = unsubscribe
mqtt_client.on_publish = publish
mqtt_client.on_message = message

try:
    print("Attempting to connect to %s!!!" % mqtt_client.broker)
    mqtt_client.connect()
except:
    print("Could not connect to %s!!!" % mqtt_client.broker)
try:
    print("Subscribing to %s" % mqtt_topic)
    mqtt_client.subscribe(mqtt_topic)
except MQTT.MMQTTException:
    print("Could not subscribe to %s!!!" % mqtt_topic)

print("---------------------------------\nWaiting for sensors to warm up...\n---------------------------------\n")
time.sleep(30)

while True:
    # Network reconnection is handled within this loop
    # loop() is called to avoid inadvertent disconnection from the MQTT server
    try:
        mqtt_client.loop()
    except (ValueError, RuntimeError) as e:
        print("Failed to get data from MQTT broker, retrying\n", e)
        wifi.reset()
        mqtt_client.reconnect()
        continue
        
    try:
        aqdata = pm25.read()
    except RuntimeError:
        print("Cannot read PM2.5, trying again later...")

    sgp30.set_iaq_relative_humidity(
        celsius=bme680.temperature + temperature_offset,
        relative_humidity=bme680.relative_humidity
    )
    # each element in the list (i.e. "temperature") needs to correspond to msg.payload.temperature in NODE-RED)
    # Assembling JSON expression with all sensor data to send over MQTT
    aqmdata = json.dumps({
        "temperature": bme680.temperature + temperature_offset,
        "humidity": bme680.relative_humidity,
        "pressure": bme680.pressure,
        "altitude": bme680.altitude,
        "gas": bme680.gas,
        "pm10": aqdata["pm10 env"],
        "pm25": aqdata["pm25 env"],
        "pm100": aqdata["pm100 env"],
        "p03um": aqdata["particles 03um"],
        "p05um": aqdata["particles 05um"],
        "p10um": aqdata["particles 10um"],
        "p25um": aqdata["particles 25um"],
        "p50um": aqdata["particles 50um"],
        "p100um": aqdata["particles 100um"],
        "eCO2": sgp30.eCO2, "TVOC": sgp30.TVOC,
        "voltage": vsensor.cell_voltage,
        "battery_percentage": vsensor.cell_percent
    })
    
    # Publish JSON file to MQTT Broker
    print("Publishing to %s" % mqtt_topic)
    mqtt_client.publish(mqtt_topic, aqmdata)
    time.sleep(15)



