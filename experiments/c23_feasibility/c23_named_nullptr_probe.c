#include <stddef.h>

int main(void) {
    nullptr_t value = nullptr;
    return value == nullptr ? 0 : 1;
}
