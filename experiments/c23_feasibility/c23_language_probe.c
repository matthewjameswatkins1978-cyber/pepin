#include <stddef.h>
#include <stdint.h>
#include <stdalign.h>

constexpr int pep_c23_constant = 23;
static_assert(sizeof(int64_t) == 8, "int64_t must be exactly 64 bits");
static_assert(alignof(max_align_t) >= alignof(void *), "standard alignment must be available");

int main(void) {
    nullptr_t null_value = nullptr;
    typeof_unqual(null_value) another_null = nullptr;
    return null_value == another_null && pep_c23_constant == 23 ? 0 : 1;
}
