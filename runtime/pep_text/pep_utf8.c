// See pep_utf8.h for the contract. Strict C23, no extensions. Validation
// follows the seed and full Pep lexer diagnostic precedence; decoding uses
// the stricter scalar boundary table because it has no diagnostic offset.
#include "pep_utf8.h"

typedef struct {
    unsigned char lo;
    unsigned char hi;
} pep_utf8_range;

static size_t lead_width(unsigned char first, pep_utf8_range *second)
{
    second->lo = 128;
    second->hi = 191;
    if (first <= 127) {
        return 1;
    }
    if (first >= 194 && first <= 223) {
        return 2;
    }
    if (first == 224) {
        second->lo = 160;
        return 3;
    }
    if (first >= 225 && first <= 236) {
        return 3;
    }
    if (first == 237) {
        second->hi = 159;
        return 3;
    }
    if (first == 238 || first == 239) {
        return 3;
    }
    if (first == 240) {
        second->lo = 144;
        return 4;
    }
    if (first >= 241 && first <= 243) {
        return 4;
    }
    if (first == 244) {
        second->hi = 143;
        return 4;
    }
    return 0;
}

static int invalid_at(size_t offset, size_t *error_offset)
{
    if (error_offset != nullptr) {
        *error_offset = offset;
    }
    return PEP_UTF8_INVALID;
}

int pep_utf8_validate(const char *s, size_t n, size_t *error_offset)
{
    size_t i = 0;
    if (s == nullptr) {
        return PEP_UTF8_BADARG;
    }
    while (i < n) {
        unsigned char first = (unsigned char)s[i];
        size_t width;
        unsigned int minimum;
        unsigned int scalar;
        size_t j;
        if (first < 0x80) {
            i += 1;
            continue;
        }
        // Use structural widths first, including C0/C1 and F5-F7. The
        // canonical lexer reports a bad continuation before scalar legality
        // for a complete sequence, and reports truncation at the lead.
        if (first >= 0xC0 && first <= 0xDF) {
            width = 2;
            minimum = 0x80;
            scalar = first & 0x1F;
        } else if (first >= 0xE0 && first <= 0xEF) {
            width = 3;
            minimum = 0x800;
            scalar = first & 0x0F;
        } else if (first >= 0xF0 && first <= 0xF7) {
            width = 4;
            minimum = 0x10000;
            scalar = first & 0x07;
        } else {
            return invalid_at(i, error_offset);
        }
        if (n - i < width) {
            return invalid_at(i, error_offset);
        }
        for (j = 1; j < width; j++) {
            unsigned char cont = (unsigned char)s[i + j];
            if (cont < 0x80 || cont > 0xBF) {
                return invalid_at(i + j, error_offset);
            }
            scalar = (scalar << 6) | (cont & 0x3F);
        }
        if (scalar < minimum || scalar > 0x10FFFF ||
            (scalar >= 0xD800 && scalar <= 0xDFFF)) {
            return invalid_at(i, error_offset);
        }
        i += width;
    }
    return PEP_UTF8_OK;
}

size_t pep_utf8_decode(const char *s, size_t n, unsigned int *cp)
{
    unsigned char first;
    pep_utf8_range second;
    size_t width;
    unsigned int value;
    size_t j;
    if (s == nullptr || n == 0) {
        return 0;
    }
    first = (unsigned char)s[0];
    width = lead_width(first, &second);
    if (width == 0 || n < width) {
        return 0;
    }
    if (width == 1) {
        if (cp != nullptr) {
            *cp = first;
        }
        return 1;
    }
    value = (unsigned int)(first & (width == 2 ? 0x1F : (width == 3 ? 0x0F : 0x07)));
    for (j = 1; j < width; j++) {
        unsigned char cont = (unsigned char)s[j];
        unsigned char lo = (j == 1) ? second.lo : 128;
        unsigned char hi = (j == 1) ? second.hi : 191;
        if (cont < lo || cont > hi) {
            return 0;
        }
        value = (value << 6) | (unsigned int)(cont & 0x3F);
    }
    if (cp != nullptr) {
        *cp = value;
    }
    return width;
}

size_t pep_utf8_encode(unsigned int cp, char out[4])
{
    if (out == nullptr) {
        return 0;
    }
    if (cp <= 0x7F) {
        out[0] = (char)cp;
        return 1;
    }
    if (cp <= 0x7FF) {
        out[0] = (char)(0xC0 | (cp >> 6));
        out[1] = (char)(0x80 | (cp & 0x3F));
        return 2;
    }
    if (cp <= 0xD7FF || (cp >= 0xE000 && cp <= 0xFFFF)) {
        out[0] = (char)(0xE0 | (cp >> 12));
        out[1] = (char)(0x80 | ((cp >> 6) & 0x3F));
        out[2] = (char)(0x80 | (cp & 0x3F));
        return 3;
    }
    if (cp >= 0x10000 && cp <= 0x10FFFF) {
        out[0] = (char)(0xF0 | (cp >> 18));
        out[1] = (char)(0x80 | ((cp >> 12) & 0x3F));
        out[2] = (char)(0x80 | ((cp >> 6) & 0x3F));
        out[3] = (char)(0x80 | (cp & 0x3F));
        return 4;
    }
    return 0;
}
