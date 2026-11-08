// See pep_num.h for the contract. Strict C23, no extensions. The digit
// loop accumulates magnitude in unsigned arithmetic, so INT64_MIN parses
// without ever negating it.
#include "pep_num.h"

int pep_parse_i64(const char *s, size_t n, long long *value, size_t *end)
{
    size_t i = 0;
    int negative = 0;
    unsigned long long mag = 0;
    unsigned long long limit;
    if (s == nullptr || value == nullptr || end == nullptr) {
        return PEP_NUM_BADARG;
    }
    *end = 0;
    if (i < n && s[i] == '-') {
        negative = 1;
        i += 1;
    }
    if (i >= n || (unsigned char)s[i] < '0' || (unsigned char)s[i] > '9') {
        return PEP_NUM_NODIGITS;
    }
    limit = negative ? 9223372036854775808ULL : 9223372036854775807ULL;
    while (i < n && (unsigned char)s[i] >= '0' && (unsigned char)s[i] <= '9') {
        unsigned int digit = (unsigned int)(s[i] - '0');
        if (mag > (limit - digit) / 10) {
            return PEP_NUM_OVERFLOW;
        }
        mag = mag * 10 + digit;
        i += 1;
    }
    if (negative) {
        if (mag == 9223372036854775808ULL) {
            *value = (-9223372036854775807LL - 1);
        } else {
            *value = -(long long)mag;
        }
    } else {
        *value = (long long)mag;
    }
    *end = i;
    return PEP_NUM_OK;
}
