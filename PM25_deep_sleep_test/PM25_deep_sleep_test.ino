/* Test sketch for Adafruit PM2.5 sensor with UART or I2C */

#include "Adafruit_PM25AQI.h"

#define uS_TO_S_FACTOR 1000000 /* Conversion factor for micro seconds to seconds */
#define TIME_TO_SLEEP 20       /* Time ESP32 will go to sleep (in seconds) */

RTC_DATA_ATTR int bootCount = 0;

Adafruit_PM25AQI aqi = Adafruit_PM25AQI();

/*
Method to print the reason by which ESP32
has been awaken from sleep
*/
void print_wakeup_reason() {
  esp_sleep_wakeup_cause_t wakeup_reason;

  wakeup_reason = esp_sleep_get_wakeup_cause();

  switch (wakeup_reason) {
    case ESP_SLEEP_WAKEUP_EXT0: Serial.println("Wakeup caused by external signal using RTC_IO"); break;
    case ESP_SLEEP_WAKEUP_EXT1: Serial.println("Wakeup caused by external signal using RTC_CNTL"); break;
    case ESP_SLEEP_WAKEUP_TIMER: Serial.println("Wakeup caused by timer"); break;
    case ESP_SLEEP_WAKEUP_TOUCHPAD: Serial.println("Wakeup caused by touchpad"); break;
    case ESP_SLEEP_WAKEUP_ULP: Serial.println("Wakeup caused by ULP program"); break;
    default: Serial.printf("Wakeup was not caused by deep sleep: %d\n", wakeup_reason); break;
  }
}

void setup() {
  // Wait for serial monitor to open
  Serial.begin(115200);
  delay(5000);

  ++bootCount;
  Serial.println("Boot number: " + String(bootCount));
  //Print the wakeup reason for ESP32
  print_wakeup_reason();
  esp_sleep_enable_timer_wakeup(TIME_TO_SLEEP * uS_TO_S_FACTOR);
  Serial.println("Setup ESP32 to sleep for every " + String(TIME_TO_SLEEP) + " Seconds");
  Serial.println("Adafruit PMSA003I Air Quality Sensor");

  // Wait one second for sensor to boot up!
  delay(5000);

  // If using serial, initialize it and set baudrate before starting!
  // Uncomment one of the following
  //Serial1.begin(9600);
  //pmSerial.begin(9600);

  // There are 3 options for connectivity!
  if (!aqi.begin_I2C()) {  // connect to the sensor over I2C
                           //if (! aqi.begin_UART(&Serial1)) { // connect to the sensor over hardware serial
                           //if (! aqi.begin_UART(&pmSerial)) { // connect to the sensor over software serial
    Serial.println("Could not find PM 2.5 sensor!");
    while (1) delay(10);
  }

  Serial.println("PM25 found!");

  PM25_AQI_Data data;

  if (!aqi.read(&data)) {
    Serial.println("Could not read from AQI");
    delay(500);  // try again in a bit!
    return;
  }
  //delay(30000);   a delay here does nothign for sensor readings, youll want to get a set of sensor readingsa for like 15 seconds and use that average
  Serial.println("AQI reading success");

  Serial.println();
  Serial.println(F("---------------------------------------"));
  Serial.println(F("Concentration Units (standard)"));
  Serial.println(F("---------------------------------------"));
  Serial.print(F("PM 1.0: "));
  Serial.print(data.pm10_standard);
  Serial.print(F("\t\tPM 2.5: "));
  Serial.print(data.pm25_standard);
  Serial.print(F("\t\tPM 10: "));
  Serial.println(data.pm100_standard);
  Serial.println(F("Concentration Units (environmental)"));
  Serial.println(F("---------------------------------------"));
  Serial.print(F("PM 1.0: "));
  Serial.print(data.pm10_env);
  Serial.print(F("\t\tPM 2.5: "));
  Serial.print(data.pm25_env);
  Serial.print(F("\t\tPM 10: "));
  Serial.println(data.pm100_env);
  Serial.println(F("---------------------------------------"));
  Serial.print(F("Particles > 0.3um / 0.1L air:"));
  Serial.println(data.particles_03um);
  Serial.print(F("Particles > 0.5um / 0.1L air:"));
  Serial.println(data.particles_05um);
  Serial.print(F("Particles > 1.0um / 0.1L air:"));
  Serial.println(data.particles_10um);
  Serial.print(F("Particles > 2.5um / 0.1L air:"));
  Serial.println(data.particles_25um);
  Serial.print(F("Particles > 5.0um / 0.1L air:"));
  Serial.println(data.particles_50um);
  Serial.print(F("Particles > 10 um / 0.1L air:"));
  Serial.println(data.particles_100um);
  Serial.println(F("---------------------------------------"));

  /*
  Now that we have setup a wake cause and if needed setup the
  peripherals state in deep sleep, we can now start going to
  deep sleep.
  In the case that no wake up sources were provided but deep
  sleep was started, it will sleep forever unless hardware
  reset occurs.
  */
  Serial.println("Going to sleep now");
  delay(1000);
  Serial.flush(); 
  esp_deep_sleep_start();
  Serial.println("This will never be printed");

}

void loop() {
}
