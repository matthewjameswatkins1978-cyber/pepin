// See pep_find.h for the contract. Strict C23, no extensions. Naive
// left-to-right scan with memcmp at each position: worst case O(hn*nn),
// best case O(hn), allocation-free and branch-predictable. No SIMD, no
// tables — obvious correctness beats cleverness for a compiler aid.
#include "pep_find.h"

#include <string.h>

int pep_text_find(const char *hay, size_t hn, const char *ndl, size_t nn, size_t *at)
{
    size_t limit;
    size_t i;
    if (hay == nullptr || ndl == nullptr || at == nullptr) {
        return PEP_FIND_BADARG;
    }
    if (nn == 0) {
        *at = 0;
        return PEP_FIND_OK;
    }
    if (nn > hn) {
        *at = hn;
        return PEP_FIND_NONE;
    }
    limit = hn - nn;
    for (i = 0; i <= limit; i++) {
        if (memcmp(hay + i, ndl, nn) == 0) {
            *at = i;
            return PEP_FIND_OK;
        }
    }
    *at = hn;
    return PEP_FIND_NONE;
}
