#include "shifter.h"
#include <Arduino.h>

shifter::shifter(uint8_t clk, uint8_t din, uint8_t clr) {
    _clk = clk;
    _din = din;
    _clr = clr;
}

// Initialises shift register with 8-bit val
void shifter::init(uint8_t val) {
  pinMode(_clk, OUTPUT);
  pinMode(_din, OUTPUT);
  pinMode(_clr, OUTPUT);

  digitalWrite(_clk, LOW);
  
  // Clear shift register
  digitalWrite(_clr, LOW);
  delay(SHIFT_DELAY);
  digitalWrite(_clr, HIGH);
  delayMicroseconds(SHIFT_DELAY);

  for (int i = 0; i < 8; i++) {
    uint8_t bit = extractBit(val, i);
    shift(bit);
    shift(0); // PCB bug means each shift is buffered/delayed by 1 cycle
  }
}

// Shift bit into register
void shifter::shift(uint8_t bit) {
  digitalWrite(_din, bit);
  digitalWrite(_clk, HIGH);
  delayMicroseconds(SHIFT_DELAY);
  digitalWrite(_clk, LOW);
  delayMicroseconds(SHIFT_DELAY);
}

uint8_t shifter::extractBit(uint8_t val, int n) {
  uint8_t mask = 1 << n;
  return (val & mask) >> n;
}