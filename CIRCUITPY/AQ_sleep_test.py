import time
import board
import busio
import digitalio
from adafruit_pm25.i2c import PM25_I2C
import adafruit_bme680
import adafruit_sgp30
import alarm
import neopixel
from adafruit_lc709203f import LC709203F

# Remove these two lines on boards without board.NEOPIXEL_POWER.
np_power = digitalio.DigitalInOut(board.NEOPIXEL_POWER)
np_power.switch_to_output(value=True)

# Assigning number and brightness of NEOPIXELs
np = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.1)

reset_pin = None

# Create library object, use 'slow' 100KHz frequency!
i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)

# Connect to i2c connectors
pm25 = PM25_I2C(i2c, reset_pin)
bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c, debug=False)
sgp30 = adafruit_sgp30.Adafruit_SGP30(i2c)
sensor = LC709203F(i2c)

# change this to match the location's pressure (hPa) at sea level
bme680.sea_level_pressure = 1013.25

print("Found PM2.5 sensor, reading data...")
print("Found BME680 sensor, reading data...")
print("SGP30 serial #", [hex(i) for i in sgp30.serial])
print("Battery: %0.3f Volts / %0.1f %%" % (sensor.cell_voltage, sensor.cell_percent))


# setting SGP30 baselines. BME680 feeds data into this
sgp30.set_iaq_baseline(0x8973, 0x8AAE)
sgp30.set_iaq_relative_humidity(celsius=bme680.temperature, relative_humidity=bme680.relative_humidity)

# You will usually have to add an offset to account for the temperature of
# the sensor. This is usually around 5 degrees but varies by use. Use a
# separate temperature sensor to calibrate this one.
temperature_offset = -5

elapsed_sec = 0

print("Sleeping for 15 seconds")
time.sleep(15)

while True:

    np[0] = (50, 250, 250)
    # time.sleep(3)
    
    print("\nTemperature: %0.1f C" % (bme680.temperature + temperature_offset))
    print("Gas: %d ohm" % bme680.gas)
    print("Humidity: %0.1f %%" % bme680.relative_humidity)
    print("Pressure: %0.3f hPa" % bme680.pressure)
    print("Altitude = %0.2f meters" % bme680.altitude)
    
    # time.sleep(3)
    
    try:
        aqdata = pm25.read()
        # print(aqdata)
    except RuntimeError:
        print("Unable to read from sensor, retrying...")
        continue

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
    
    # time.sleep(3)
    
    print("eCO2 = %d ppm \t TVOC = %d ppb" % (sgp30.eCO2, sgp30.TVOC))
    elapsed_sec += 9
    if elapsed_sec > 5:
        elapsed_sec = 0
        print(
            "**** Baseline values: eCO2 = 0x%x, TVOC = 0x%x"
            % (sgp30.baseline_eCO2, sgp30.baseline_TVOC)
        )
        
    time.sleep(5)
    # Create a an alarm that will trigger 10 seconds from now.
    time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 5)
    # Exit the program, and then deep sleep until the alarm wakes us.
    alarm.exit_and_deep_sleep_until_alarms(time_alarm)
    # Does not return, so we never get here.