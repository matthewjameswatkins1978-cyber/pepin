// Agent-4 number probe: parses each argv entry with pep_parse_i64 and
// round-trips fixed Int64 constants through append_i64/parse_i64.
// Prints one line per check; the suite asserts exact output on both
// toolchains. Binary stdout so bytes are exact on Windows.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "pep_num.h"
#include "pep_textbuf.h"

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

static void check_parse(const char *text)
{
    long long value = 0;
    size_t end = 0;
    int status = pep_parse_i64(text, strlen(text), &value, &end);
    if (status == PEP_NUM_OK) {
        (void)printf("p %lld %llu\n", value, (unsigned long long)end);
    } else if (status == PEP_NUM_NODIGITS) {
        (void)printf("p nodigits\n");
    } else if (status == PEP_NUM_OVERFLOW) {
        (void)printf("p overflow\n");
    } else {
        (void)printf("p badarg\n");
    }
}

static int check_roundtrip(long long original)
{
    pep_textbuf_t buf;
    long long back = 0;
    size_t end = 0;
    int status;
    if (pep_textbuf_init(&buf) != 0) {
        return 1;
    }
    status = pep_textbuf_append_i64(&buf, original);
    if (status != 0) {
        pep_textbuf_free(&buf);
        return 1;
    }
    status = pep_parse_i64(pep_textbuf_cstr(&buf), pep_textbuf_len(&buf), &back, &end);
    if (status != PEP_NUM_OK || back != original || end != pep_textbuf_len(&buf)) {
        pep_textbuf_free(&buf);
        return 1;
    }
    (void)printf("r %lld\n", back);
    pep_textbuf_free(&buf);
    return 0;
}

int main(int argc, char **argv)
{
    static const long long fixed[] = {
        0LL, 1LL, -1LL, 42LL, -42LL,
        9223372036854775807LL, (-9223372036854775807LL - 1),
        1234567890123456789LL, -1234567890123456789LL
    };
    size_t i;
    int arg;
#ifdef _WIN32
    (void)_setmode(_fileno(stdout), _O_BINARY);
#endif
    for (arg = 1; arg < argc; arg++) {
        check_parse(argv[arg]);
    }
    for (i = 0; i < sizeof fixed / sizeof fixed[0]; i++) {
        if (check_roundtrip(fixed[i]) != 0) {
            return 1;
        }
    }
    return 0;
}
