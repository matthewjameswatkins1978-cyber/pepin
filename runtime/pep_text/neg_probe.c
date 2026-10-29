// Agent-4 negative probe: pins every null-argument path and the sticky
// error contract in one deterministic run. Prints `n ...` with the
// BADARG codes in fixed order, then `s ...` with the sticky codes after
// forcing an overflow. The suite asserts exact output on both toolchains.
#include <stdio.h>

#include "pep_json.h"
#include "pep_num.h"
#include "pep_span.h"
#include "pep_textbuf.h"
#include "pep_utf8.h"

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

int main(void)
{
    pep_textbuf_t buf;
    long long value = 0;
    size_t end = 0;
#ifdef _WIN32
    /* Byte-exact stdout on Windows; see span_probe. Test-driver-only. */
    (void)_setmode(_fileno(stdout), _O_BINARY);
#endif
    (void)printf("n %d %d %d %d %d %d %d\n",
        pep_json_escape(nullptr, "x", 1),
        pep_parse_i64(nullptr, 1, &value, &end),
        pep_textbuf_read_file(nullptr, "x"),
        pep_textbuf_write_file(nullptr, "x"),
        pep_textbuf_reserve(nullptr, 1),
        pep_textbuf_append_bytes(nullptr, "x", 1),
        pep_textbuf_join(nullptr, nullptr, 1));
    if (pep_textbuf_init(&buf) != 0) {
        return 1;
    }
    if (pep_textbuf_reserve(&buf, (size_t)-1) != PEP_TEXTBUF_OVERFLOW) {
        pep_textbuf_free(&buf);
        return 1;
    }
    (void)printf("s %d %d %d\n",
        pep_textbuf_append_cstr(&buf, "x"),
        pep_textbuf_write(&buf, stdout),
        pep_textbuf_read_file(&buf, "x"));
    pep_textbuf_free(&buf);
    return 0;
}
