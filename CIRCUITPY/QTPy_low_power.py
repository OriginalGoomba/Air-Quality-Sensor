import alarm
import ssl
import socketpool
import wifi
import json
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import adafruit_bme680
import time
import board
import busio
from digitalio import DigitalInOut, Direction, Pull
import adafruit_sgp30
from adafruit_pm25.i2c import PM25_I2C

print("Waking from sleep")

i2c = board.STEMMA_I2C()

reset_pin = None

pm25 = PM25_I2C(i2c, reset_pin)
sgp30 = adafruit_sgp30.Adafruit_SGP30(i2c)
bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c)
temperature_offset = -5
bme680.sea_level_pressure = 1013.25
sgp30.set_iaq_baseline(0x8973, 0x8AAE)
sgp30.set_iaq_relative_humidity(celsius=22.1, relative_humidity=44)
# Add a secrets.py to your filesystem that has a dictionary called secrets with "ssid" and
# "password" keys with your WiFi credentials. DO NOT share that file or commit it into Git or other
# source control.
# pylint: disable=no-name-in-module,wrong-import-order

bme680.temperature_oversample
bme680.humidity_oversample
bme680.pressure_oversample

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

print("Connecting to %s" % secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["password"])
print("Connected to %s!" % secrets["ssid"])

### Topic Setup ###

# MQTT Topic
# Use this topic if you'd like to connect to a standard MQTT broker
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




print("Attempting to connect to %s" % mqtt_client.broker)
mqtt_client.connect()

print("Subscribing to %s" % mqtt_topic)
mqtt_client.subscribe(mqtt_topic)



    
try:
    aqdata = pm25.read()
except RuntimeError:
    print("Unable to read from sensor, retrying...")

    
print()
print("Concentration Units (standard)")
print("---------------------------------------")
print(
    "PM 1.0: %d\tPM2.5: %d\tPM10: %d"
    % (aqdata["pm10 standard"], aqdata["pm25 standard"], aqdata["pm100 standard"])
)
print("Concentration Units (environmental)")
print("---------------------------------------")
print(
    "PM 1.0: %d\tPM2.5: %d\tPM10: %d"
    % (aqdata["pm10 env"], aqdata["pm25 env"], aqdata["pm100 env"])
)
print("---------------------------------------")
print("Particles > 0.3um / 0.1L air:", aqdata["particles 03um"])
print("Particles > 0.5um / 0.1L air:", aqdata["particles 05um"])
print("Particles > 1.0um / 0.1L air:", aqdata["particles 10um"])
print("Particles > 2.5um / 0.1L air:", aqdata["particles 25um"])
print("Particles > 5.0um / 0.1L air:", aqdata["particles 50um"])
print("Particles > 10 um / 0.1L air:", aqdata["particles 100um"])
print("---------------------------------------")
    
print("eCO2 = %d ppm \t TVOC = %d ppb" % (sgp30.eCO2, sgp30.TVOC))
    
print("\nTemperature: %0.1f C" % (bme680.temperature + temperature_offset))
print("Gas: %d ohm" % bme680.gas)
print("Humidity: %0.1f %%" % bme680.relative_humidity)
print("Pressure: %0.3f hPa" % bme680.pressure)
print("Altitude = %0.2f meters" % bme680.altitude)
# each element in the list (i.e. "temperature") needs tro correspond to msg.payload.temperature in NODE-RED)
bme680data = {"temperature":bme680.temperature + temperature_offset, 
"humidity":bme680.relative_humidity, "pressure":bme680.pressure, "altitude":bme680.altitude}
data_out = json.dumps(bme680data)
    
aqmdata = json.dumps({"temperature":bme680.temperature + temperature_offset, "humidity":bme680.relative_humidity, "pressure":bme680.pressure, "altitude":bme680.altitude, "gas":bme680.gas, "pm10":aqdata["pm10 env"], "pm25":aqdata["pm25 env"], "pm100":aqdata["pm100 env"], "p03um":aqdata["particles 03um"], "p05um":aqdata["particles 05um"], "p10um":aqdata["particles 10um"], "p25um":aqdata["particles 25um"], "p50um":aqdata["particles 50um"], "p100um":aqdata["particles 100um"], "eCO2":sgp30.eCO2, "TVOC":sgp30.TVOC})
print(aqmdata)
print("Publishing to %s" % mqtt_topic)
mqtt_client.publish(mqtt_topic, aqmdata)
# time.sleep(10)

# print("Unsubscribing from %s" % mqtt_topic)
# mqtt_client.unsubscribe(mqtt_topic)

print("Disconnecting from %s" % mqtt_client.broker)
mqtt_client.disconnect()

print("Going to sleep")
# Create a an alarm that will trigger 20 seconds from now.
time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 20)
# Exit the program, and then deep sleep until the alarm wakes us.
alarm.exit_and_deep_sleep_until_alarms(time_alarm)
# Does not return, so we never get here.
