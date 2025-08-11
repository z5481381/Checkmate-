#include "board.h"
#include <Arduino.h>

board::board(uint8_t shiftClkPin, uint8_t shiftDPin, uint8_t shiftClrPin, const uint8_t *colPins, uint8_t numLEDs)
  : _shiftClkPin(shiftClkPin),
    _shiftDPin(shiftDPin),
    _shiftClrPin(shiftClrPin),
    _colPins(colPins),
    _shifter(shiftClkPin, shiftDPin, shiftClrPin),
    _numLEDs(numLEDs)
{
  for (int i = 0; i < COLS; i++) {
    pinMode(colPins[i], INPUT);
  }

  _state = 0;

  _leds = new CRGB[numLEDs];
  for (int i = 0; i < numLEDs; i++) {
    _leds[i] = CRGB::Black;
  }
  FastLED.addLeds<WS2812, LED_PIN, GRB>(_leds, numLEDs);
  FastLED.clear();
  FastLED.show();  // Clear all at startup
}

board::~board() {
  delete[] _leds;
}

void board::init() {
  // Setup BLE
  Serial.println("Setting up BLE...");
  BLEDevice::init(DEVICE_NAME);
  pServer = BLEDevice::createServer();
  pService = pServer->createService(BLEUUID(SERVICE_UUID), 20);
  
  // Create board state characteristic as read-only
  boardStateCharacteristic =
    pService->createCharacteristic(BOARD_STATE_UUID, BLECharacteristic::PROPERTY_READ);
  boardStateCharacteristic->setValue(uint64_to_string(0));

  // Create LED characteristic as read/write
  ledRowCharacteristic = pService->createCharacteristic(LED_ROW_UUID, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE);
  ledRowCharacteristic->setValue("0");
  ledColCharacteristic = pService->createCharacteristic(LED_COL_UUID, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE);
  ledColCharacteristic->setValue("0");
  ledRCharacteristic = pService->createCharacteristic(LED_R_UUID, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE);
  ledRCharacteristic->setValue("0");
  ledGCharacteristic = pService->createCharacteristic(LED_G_UUID, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE);
  ledGCharacteristic->setValue("0");
  ledBCharacteristic = pService->createCharacteristic(LED_B_UUID, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE);
  ledBCharacteristic->setValue("0");
  doneCharacteristic = pService->createCharacteristic(DONE_UUID, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE);
  doneCharacteristic->setValue("0");
  lcdCharacteristic = pService->createCharacteristic(LCD_UUID, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE);
  lcdCharacteristic->setValue("0");

  // Begin server
  pService->start();
  pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x06);
  pAdvertising->setMinPreferred(0x12);
  BLEDevice::startAdvertising();
}

uint64_t board::scan() {
  uint64_t sensors = 0;

  _shifter.init(0b10000000);

  for (int n = 0; n < ROWS; n++) {
    uint8_t colVals = 0;
    for (int i = COLS - 1; i >= 0; i--) {
      colVals = (colVals << 1) + digitalRead(_colPins[i]);
    }

    sensors = (sensors << 8) + (uint64_t)colVals;
    _shifter.shift(0);
  }

  _state = sensors;
  _state += ((uint64_t)2 << 53) + ((uint64_t)2 << 47) + ((uint64_t)2 << 60) + ((uint64_t)2 << 6) + ((uint64_t)2 << 58) +  ((uint64_t)2 << 49) + ((uint64_t)2 << 12) + ((uint64_t)2 << 1);
  return _state;
}

void board::print() {
  Serial.println(_state, BIN);
  Serial.println("Board status:");

  for (int row = 0; row < ROWS; row++) {
    for (int col = 0; col < COLS; col++) {
      uint8_t square = bitRead((uint8_t)(_state >> (8*(ROWS - row - 1))), COLS - col - 1);
      Serial.print(square);
    }
    Serial.println("");
  }
}

void board::setLED(uint8_t row, uint8_t col, uint8_t r, uint8_t g, uint8_t b) {
  uint8_t ledIndex = coordsToIndex(col, row);
  _leds[ledIndex] = CRGB(r, g, b);
}

uint8_t board::coordsToIndex(uint8_t x, uint8_t y) {
  uint8_t index;

  if (x % 2 == 0) {
    index = (COLS-x-1)*ROWS + ROWS-y-1;
  } else {
    index = (COLS-x-1)*ROWS + y;
  }

  return index;
}

void board::showLED() {
  FastLED.show();
}

void board::clearLED() {
  FastLED.clear();
  showLED();
}

void board::sendBoardState(uint64_t boardState) {
  // Note that transmission only accepts strings
  boardStateCharacteristic->setValue(uint64_to_string(boardState));
}

struct board::ledVal board::receiveLED() {
  int row = ledRowCharacteristic->getValue().toInt();
  int col = ledColCharacteristic->getValue().toInt();
  int r = ledRCharacteristic->getValue().toInt();
  int g = ledGCharacteristic->getValue().toInt();
  int b = ledBCharacteristic->getValue().toInt();

  board::ledVal led = {row, col, r, g, b};

  int done = rxDone();
  if (done == -1) {
    clearLED();
  } else if (done == 1) {
    setLED(led.row, led.col, led.r/5, led.g/5, led.b/5);
    showLED();
  }

  return led;
}

bool board::isLEDRed(int row, int col) {
  uint8_t ledIndex = coordsToIndex(col, row);

  if (_leds[ledIndex].r == 2) {
    return true;
  } else {
    return false;
  }
}

int board::rxDone() {
  int done = doneCharacteristic->getValue().toInt();
  setDone("0");

  if (done == 10) {
    clearBLE();
    return -1;
  }

  if (done == 1) {
    return 1;
  }

  return 0;
}

void board::setDone(String done) {
  doneCharacteristic->setValue(done);
}

void board::clearBLE() {
  ledRowCharacteristic->setValue("0");
  ledColCharacteristic->setValue("0");
  ledRCharacteristic->setValue("0");
  ledGCharacteristic->setValue("0");
  ledBCharacteristic->setValue("0");
}

String board::getLCDMessage() {
  String message = lcdCharacteristic->getValue();
  return message;
}

// ChatGPT conversion function
String board::uint64_to_string(uint64_t value) {
    if (value == 0) return "0";

    char buffer[21];  // Max uint64_t has 20 digits + null terminator
    int i = 20;
    buffer[i] = '\0';
    while (value > 0 && i > 0) {
        buffer[--i] = '0' + (value % 10);
        value /= 10;
    }
    return String(&buffer[i]);
}
