#include "Waveshare_LCD1602.h"
#include <Arduino.h>
#include <string.h>

Waveshare_LCD1602::Waveshare_LCD1602(uint8_t cols, uint8_t rows, uint8_t address, TwoWire& wirePort) {
    _cols = cols;
    _rows = rows;
    _lcdAddr = address;
    _wire = &wirePort;
}

void Waveshare_LCD1602::init() {
    _showfunction = LCD_4BITMODE | LCD_1LINE | LCD_5x8DOTS;
    begin(_cols, _rows);
}

void Waveshare_LCD1602::begin(uint8_t cols, uint8_t lines) {
    if (lines > 1) {
        _showfunction |= LCD_2LINE;
    }
    _numlines = lines;
    _currline = 0;

    delay(50);
    command(LCD_FUNCTIONSET | _showfunction);
    delay(5);
    command(LCD_FUNCTIONSET | _showfunction);
    delay(5);
    command(LCD_FUNCTIONSET | _showfunction);

    _showcontrol = LCD_DISPLAYON | LCD_CURSOROFF | LCD_BLINKOFF;
    display();
    clear();

    _showmode = LCD_ENTRYLEFT | LCD_ENTRYSHIFTDECREMENT;
    command(LCD_ENTRYMODESET | _showmode);
}

void Waveshare_LCD1602::command(uint8_t value) {
    uint8_t data[2] = {0x80, value};
    send(data, 2);
}

void Waveshare_LCD1602::send(uint8_t *data, uint8_t len) {
    _wire->beginTransmission(_lcdAddr);
    for (int i = 0; i < len; i++) {
        _wire->write(data[i]);
        delay(5);
    }
    _wire->endTransmission();
}

void Waveshare_LCD1602::display() {
    _showcontrol |= LCD_DISPLAYON;
    command(LCD_DISPLAYCONTROL | _showcontrol);
}

void Waveshare_LCD1602::clear() {
    command(LCD_CLEARDISPLAY);
    delayMicroseconds(2000);
}

void Waveshare_LCD1602::setCursor(uint8_t col, uint8_t row) {
    col = (row == 0 ? col | 0x80 : col | 0xC0);
    uint8_t data[2] = {0x80, col};
    send(data, 2);
}

void Waveshare_LCD1602::write_char(uint8_t value) {
    uint8_t data[2] = {0x40, value};
    send(data, 2);
}

void Waveshare_LCD1602::send_string(const char *str) {
    for (uint8_t i = 0; str[i] != '\0'; i++) {
        write_char(str[i]);
    }
}

void Waveshare_LCD1602::stopBlink() {
    _showcontrol &= ~LCD_BLINKON;
    command(LCD_DISPLAYCONTROL | _showcontrol);
}

void Waveshare_LCD1602::blink() {
    _showcontrol |= LCD_BLINKON;
    command(LCD_DISPLAYCONTROL | _showcontrol);
}

void Waveshare_LCD1602::noCursor() {
    _showcontrol &= ~LCD_CURSORON;
    command(LCD_DISPLAYCONTROL | _showcontrol);
}

void Waveshare_LCD1602::cursor() {
    _showcontrol |= LCD_CURSORON;
    command(LCD_DISPLAYCONTROL | _showcontrol);
}

void Waveshare_LCD1602::scrollDisplayLeft() {
    command(LCD_CURSORSHIFT | LCD_DISPLAYMOVE | LCD_MOVELEFT);
}

void Waveshare_LCD1602::scrollDisplayRight() {
    command(LCD_CURSORSHIFT | LCD_DISPLAYMOVE | LCD_MOVERIGHT);
}

void Waveshare_LCD1602::leftToRight() {
    _showmode |= LCD_ENTRYLEFT;
    command(LCD_ENTRYMODESET | _showmode);
}

void Waveshare_LCD1602::rightToLeft() {
    _showmode &= ~LCD_ENTRYLEFT;
    command(LCD_ENTRYMODESET | _showmode);
}

void Waveshare_LCD1602::noAutoscroll() {
    _showmode &= ~LCD_ENTRYSHIFTINCREMENT;
    command(LCD_ENTRYMODESET | _showmode);
}

void Waveshare_LCD1602::autoscroll() {
    _showmode |= LCD_ENTRYSHIFTINCREMENT;
    command(LCD_ENTRYMODESET | _showmode);
}

void Waveshare_LCD1602::customSymbol(uint8_t location, uint8_t charmap[]) {
    location &= 0x7;
    command(LCD_SETCGRAMADDR | (location << 3));
    
    uint8_t data[9];
    data[0] = 0x40;
    for (int i = 0; i < 8; i++) {
        data[i + 1] = charmap[i];
    }
    send(data, 9);
}

void Waveshare_LCD1602::home() {
    command(LCD_RETURNHOME);
    delayMicroseconds(2000);
}
