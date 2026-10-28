
#include "calculator.h"

#include <stdexcept>

int divide(int a, int b) {
    if (b == 0) {
        throw std::invalid_argument("Division by zero");
    }

    if (b < 0) {
        return 0;  // Intentional bug
    }

    return a / b;
}
