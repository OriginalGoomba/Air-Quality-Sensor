# SPDX-FileCopyrightText: 2017 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""CircuitPython Essentials Storage logging example"""
import time
import board
import digitalio
import busio
import microcontroller
import adafruit_sgp30


# For most CircuitPython boards:
#led = digitalio.DigitalInOut(board.LED)
# For QT Py M0:
led = digitalio.DigitalInOut(board.SCK)
led.switch_to_output()

i2c = board.STEMMA_I2C()

# Create library object on our I2C port
sgp30 = adafruit_sgp30.Adafruit_SGP30(i2c)

print("SGP30 serial #", [hex(i) for i in sgp30.serial])


print(sgp30.get_iaq_baseline())

sgp30.set_iaq_relative_humidity(celsius=22.1, relative_humidity=48)

elapsed_sec = 0

try:
    with open("/baselines.txt", "a") as fp:

        # read baselines for SGP30
        #for line in fp:
        #    pass
        #last_line = line
        #print(last_line)

        while True:

            print("eCO2 = %d ppm \t TVOC = %d ppb" % (sgp30.eCO2, sgp30.TVOC))
            time.sleep(1)
            elapsed_sec += 1
            if elapsed_sec > 10:
                elapsed_sec = 0
                print(
                "**** Baseline values: eCO2 = 0x%x, TVOC = 0x%x"
                % (sgp30.baseline_eCO2, sgp30.baseline_TVOC)
                )
                print(sgp30.get_iaq_baseline())

                #temp = microcontroller.cpu.temperature
                # do the C-to-F conversion here if you would like
                fp.write('0x{0:x}, 0x{0:x}'.format(sgp30.baseline_eCO2, sgp30.baseline_TVOC))
                # fp.write(sgp30.baseline_eCO2 + ", " + sgp30.baseline_TVOC + "\n")
                fp.flush()
                led.value = not led.value
                time.sleep(1)
except OSError as e:  # Typically when the filesystem isn't writeable...
    delay = 0.5  # ...blink the LED every half second.
    if e.args[0] == 28:  # If the file system is full...
        delay = 0.25  # ...blink the LED faster!
    while True:
        led.value = not led.value
        time.sleep(delay)
