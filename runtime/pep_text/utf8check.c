// Agent-4 utf8check: a real native application on the text runtime.
// Usage: utf8check FILE...  For each file prints `FILE: ok` or
// `FILE:OFFSET: invalid UTF-8` (`OFFSET` is the first bad byte, matching
// pep_utf8_validate) or `FILE: cannot read`. Exit 0 only when every file
// is valid UTF-8. Binary stdout so checked-in fixtures stay byte-exact.
#include <stdio.h>

#include "pep_textbuf.h"
#include "pep_utf8.h"

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

int main(int argc, char **argv)
{
    int bad = 0;
    int arg;
#ifdef _WIN32
    (void)_setmode(_fileno(stdout), _O_BINARY);
#endif
    if (argc < 2) {
        (void)fputs("usage: utf8check FILE...\n", stderr);
        return 2;
    }
    for (arg = 1; arg < argc; arg++) {
        pep_textbuf_t bytes;
        size_t error_at = 0;
        int status;
        if (pep_textbuf_init(&bytes) != 0) {
            return 1;
        }
        status = pep_textbuf_read_file(&bytes, argv[arg]);
        if (status != 0) {
            (void)printf("%s: cannot read\n", argv[arg]);
            pep_textbuf_free(&bytes);
            bad = 1;
            continue;
        }
        if (pep_utf8_validate(pep_textbuf_cstr(&bytes), pep_textbuf_len(&bytes), &error_at) == 0) {
            (void)printf("%s: ok\n", argv[arg]);
        } else {
            (void)printf("%s:%llu: invalid UTF-8\n", argv[arg], (unsigned long long)error_at);
            bad = 1;
        }
        pep_textbuf_free(&bytes);
    }
    return bad ? 1 : 0;
}
