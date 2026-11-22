/* Independent native UTF-8 probe. Input: one hex-encoded byte string per
 * line (0-32 bytes). Output: validate status, error offset,
 * decoded first-scalar width and value. Sentinels must survive failures.
 */
#include "pep_utf8.h"

#include <stdio.h>
#include <string.h>

static int hex_digit(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    return -1;
}

int main(void)
{
    char line[66];
    size_t untouched = 999;
    unsigned int scalar = 0xFFFFFFFFu;
    if (pep_utf8_validate(nullptr, 0, &untouched) != PEP_UTF8_BADARG ||
        untouched != 999 || pep_utf8_decode(nullptr, 0, &scalar) != 0 ||
        scalar != 0xFFFFFFFFu) return 4;
    while (fgets(line, sizeof line, stdin) != nullptr) {
        char bytes[32];
        size_t n = strlen(line);
        size_t offset = 999;
        unsigned int cp = 0xFFFFFFFFu;
        if (n == 0 || line[n - 1] != '\n') return 2;
        n--;
        if (n % 2 != 0) return 2;
        for (size_t i = 0; i < n; i += 2) {
            int hi = hex_digit(line[i]);
            int lo = hex_digit(line[i + 1]);
            if (hi < 0 || lo < 0) return 2;
            bytes[i / 2] = (char)(hi * 16 + lo);
        }
        int status = pep_utf8_validate(bytes, n / 2, &offset);
        size_t width = pep_utf8_decode(bytes, n / 2, &cp);
        if (pep_utf8_validate(bytes, n / 2, nullptr) != status ||
            pep_utf8_decode(bytes, n / 2, nullptr) != width) return 4;
        if (printf("%d %zu %zu %u\n", status, offset, width, cp) < 0) return 3;
    }
    return ferror(stdin) || ferror(stdout) ? 3 : 0;
}
