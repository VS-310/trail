
#include "calculator.h"

#include <cassert>
#include <stdexcept>

int main() {
    assert(divide(10, 2) == 5);
    assert(divide(10, -2) == -5);
    assert(divide(-10, -2) == 5);
    assert(divide(-10, 2) == -5);

    bool threw = false;

    try {
        divide(10, 0);
    } catch (const std::invalid_argument&) {
        threw = true;
    }

    assert(threw);

    return 0;
}
