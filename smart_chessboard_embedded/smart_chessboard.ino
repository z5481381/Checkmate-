#include "board.h"
#include <Wire.h>
#include "Waveshare_LCD1602.h"

TwoWire I2C_LCD1 = TwoWire(0);  // First I2C bus
TwoWire I2C_LCD2 = TwoWire(1);  // Second I2C bus

// PINS
#define SDA1 11
#define SCL1 10

#define SDA2 13
#define SCL2 12

#define SHIFT_CLK 38
#define SHIFT_IN 48
#define SHIFT_CLR 2

#define NUM_LEDS 8*8

// I2C address of both displays (fixed)
#define LCD_I2C_ADDRESS 0x3E

// Declare LCD screen objects
Waveshare_LCD1602 lcd1(16, 2, LCD_I2C_ADDRESS, I2C_LCD1);
Waveshare_LCD1602 lcd2(16, 2, LCD_I2C_ADDRESS, I2C_LCD2);
String prevMessage = "";

// Declare chessboard object
// constexpr uint8_t colPins[] = {6, 7, 15, 16, 17, 18, 8, 9};
constexpr uint8_t colPins[] = {9, 8, 18, 17, 16, 15, 7, 6};
board board(SHIFT_CLK, SHIFT_IN, SHIFT_CLR, colPins, NUM_LEDS);

uint64_t prev_state = 0;

void setup() {
  Serial.begin(115200);
  // while (!Serial);

  // Initialize both I2C buses
  I2C_LCD1.begin(SDA1, SCL1);
  I2C_LCD2.begin(SDA2, SCL2);

  // Initialize each LCD
  lcd1.init();
  lcd2.init();

  delay(500);
  board.init();
}

void loop() {
  uint64_t sensors = board.scan();
  board.sendBoardState(sensors);
  // board.print();

  board::ledVal led = board.receiveLED();
  // board.setLED(led.row, led.col, led.r/5, led.g/5, led.b/5);
  Serial.print(" Row: ");
  Serial.print(led.row);
  Serial.print(" Col: ");
  Serial.print(led.col);
  Serial.print(" R: ");
  Serial.print(led.r);
  Serial.print(" G: ");
  Serial.print(led.g);
  Serial.print(" B: ");
  Serial.println(led.b);

  int currentLED = 0;
  for (int row = 0; row < 8; row++) {
    for (int col = 0; col < 8; col++) {
      uint8_t square = bitRead((uint8_t)(sensors >> (8*(8 - row - 1))), 8 - col - 1);
      
      if (square == 1) {
        board.setLED(row, col, 2, 0, 0);
      } else if (board.isLEDRed(row, col)) {
        board.setLED(row, col, 0, 0, 0);
      }

      currentLED++;
    }
  }

  if (prev_state != sensors) {
    prev_state = sensors;
    board.showLED();
  }
  
  // int done = board.rxDone();
  // if (done == -1) {
  //   board.clearLED();
  // } else if (done == 1) {
  //   board.showLED();
  // }

  String message = board.getLCDMessage();
  if (message != prevMessage) {
    prevMessage = message;
    String line1 = message.substring(0, 11);
    String line2 = message.substring(11);

    lcd1.clear();
    lcd1.setCursor(0, 0);
    lcd1.send_string(line1.c_str());
    lcd1.setCursor(0, 1);
    lcd1.send_string(line2.c_str());
    
    lcd2.clear();
    lcd2.setCursor(0, 0);
    lcd2.send_string(line1.c_str());
    lcd2.setCursor(0, 1);
    lcd2.send_string(line2.c_str());
  }
}
