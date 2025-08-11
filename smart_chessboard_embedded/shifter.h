#include <inttypes.h>

// Signal half-periods in us
#define SHIFT_DELAY 100

class shifter {
public:
    shifter(uint8_t clk, uint8_t din, uint8_t clr);
    
    void init(uint8_t val);
    void shift(uint8_t bit);

private:
    uint8_t extractBit(uint8_t val, int n);
    uint8_t _clk, _din, _clr;
};