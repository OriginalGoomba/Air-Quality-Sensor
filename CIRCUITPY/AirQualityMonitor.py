import alarm
import ssl
import socketpool
import wifi
import json
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import adafruit_bme680
import time
import board
import digitalio
import adafruit_sgp30
from adafruit_pm25.i2c import PM25_I2C
from adafruit_lc709203f import LC709203F

# Reset the count if we haven't slept yet. This is used to cycle count on battery.
if not alarm.wake_alarm:
    # Use byte 5 in sleep memory. This is just an example.
    alarm.sleep_memory[5] = 0

print("Waking from sleep. Cycles: ", alarm.sleep_memory[5])
time.sleep(5)

alarm.sleep_memory[5] = (alarm.sleep_memory[5] + 1) % 256
i2c = board.STEMMA_I2C()

reset_pin = None

pm25 = PM25_I2C(i2c, reset_pin)
aqdata = {}
sgp30 = adafruit_sgp30.Adafruit_SGP30(i2c)
bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c, address=0x76)
temperature_offset = -5
bme680.sea_level_pressure = 1013.25
sgp30.set_iaq_baseline(0x8973, 0x8AAE)
sgp30.set_iaq_relative_humidity(celsius=22.1, relative_humidity=44)
vsensor = LC709203F(i2c)

print("Battery: %0.3f Volts / %0.1f %%" % (vsensor.cell_voltage, vsensor.cell_percent))

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

try:
    print("Connecting to %s" % secrets["ssid"])
    wifi.radio.connect(secrets["ssid"], secrets["password"])
    print("Connected to %s!" % secrets["ssid"])
except ConnectionError:
    print("Unable to connect to %s" % secrets["ssid"])


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

# Attempting to read PM25 sensor data, typically needs ~10 seconds after wake
try:
    time.sleep(10)
    aqdata = pm25.read()
    print(type(aqdata))
except RuntimeError:
    print("Cannot read PM2.5, trying again later...")
    
# debug print out of PM2.5 sensor data
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

# debug redout of SGP30 data, this also needs ~10 seconds to come up to temperature
print("eCO2 = %d ppm \t TVOC = %d ppb" % (sgp30.eCO2, sgp30.TVOC))

# debug readout of BME680
print("\nTemperature: %0.1f C" % (bme680.temperature + temperature_offset))
print("Gas: %d ohm" % bme680.gas)
print("Humidity: %0.1f %%" % bme680.relative_humidity)
print("Pressure: %0.3f hPa" % bme680.pressure)
print("Altitude = %0.2f meters" % bme680.altitude)
# each element in the list (i.e. "temperature") needs tro correspond to msg.payload.temperature in NODE-RED)

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
    "battery_percentage": vsensor.cell_percent, 
    "cycles": alarm.sleep_memory[5]
})

# debug printout of sensor data
print(aqmdata)

# publishing to MQTT on raspberry pi
print("Publishing to %s" % mqtt_topic)
mqtt_client.publish(mqtt_topic, aqmdata)

# disconnect before sleep
print("Disconnecting from %s" % mqtt_client.broker)
mqtt_client.disconnect()

print("Going to sleep")

# turning off I2C power before sleep to turn off sensors and save power
i2c_power = digitalio.DigitalInOut(board.I2C_POWER)
i2c_power.switch_to_input()

# Create a an alarm that will trigger 20 seconds from now.
time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 5)
# Exit the program, and then deep sleep until the alarm wakes us.
alarm.exit_and_deep_sleep_until_alarms(time_alarm)
# Does not return, so we never get here.
