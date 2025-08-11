#include "shifter.h"
#include <inttypes.h>
#include <FastLED.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>

#define ROWS 8
#define COLS 8

#define LED_PIN 47

#define SERVICE_UUID       "22c2b227-b1b7-4a09-babb-e1d6b701183d"
#define BOARD_STATE_UUID   "7a96b8e3-41bc-428d-8f52-5601235c2dca"
#define LED_ROW_UUID       "7d4a35e3-84b4-42b3-b279-5d9b9f28f5fd"
#define LED_COL_UUID       "56d86c37-0273-4671-b8c0-e0fe74e1b4c0"
#define LED_R_UUID         "0f5a6555-250d-41f8-b318-7a0ff4737169"
#define LED_G_UUID         "738ea3b6-8ccc-4b19-a3da-48149c95b74f"
#define LED_B_UUID         "bc424431-dd9b-4cda-a1ab-5cbc8f62388c"
#define DONE_UUID          "4657f152-f696-4bfa-96f2-0f9e932a7319"
#define LCD_UUID           "aee33363-c3d9-49c0-b7e5-d0d58339c687"

#define DEVICE_NAME "Checkmate+"

class board {
public:
  struct ledVal {
    int row;
    int col;
    int r;
    int g;
    int b;
  };

  board(uint8_t shiftClkPin, uint8_t shiftDPin, uint8_t shiftClrPin, const uint8_t *colPins, uint8_t numLEDs);
  ~board();

  void init();
  uint64_t scan();
  void print();
  void setLED(uint8_t row, uint8_t col, uint8_t r, uint8_t g, uint8_t b);
  void showLED();
  void sendBoardState(uint64_t boardState);
  struct ledVal receiveLED();
  int rxDone();
  void setDone(String done);
  void clearLED();
  bool isLEDRed(int row, int col);
  String getLCDMessage();

private:
  void clearBLE();
  uint8_t coordsToIndex(uint8_t x, uint8_t y);
  String uint64_to_string(uint64_t value);

  uint8_t _shiftClkPin, _shiftDPin, _shiftClrPin, _numLEDs;
  const uint8_t *_colPins;

  uint64_t _state;
  shifter _shifter;

  CRGB *_leds;

  BLEServer *pServer;
  BLEService *pService;
  BLECharacteristic *boardStateCharacteristic;
  BLECharacteristic *ledRowCharacteristic;
  BLECharacteristic *ledColCharacteristic;
  BLECharacteristic *ledRCharacteristic;
  BLECharacteristic *ledGCharacteristic;
  BLECharacteristic *ledBCharacteristic;
  BLECharacteristic *doneCharacteristic;
  BLECharacteristic *lcdCharacteristic;
  BLEAdvertising *pAdvertising;
};