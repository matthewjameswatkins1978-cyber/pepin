// Agent-4 file probe: exercises the whole native text pipeline in one
// program: read a file into the builder, validate its UTF-8, render one
// diagnostic block per requested offset, write the bytes back out.
// Usage: file_probe IN OUT LABEL OFF...  Prints null-path codes first
// (`n a b c d`), then `v ok` or `v err OFF`, one diag block per offset,
// then `w ok LEN`. A missing input prints `r io` and exits 1.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

#include "pep_span.h"
#include "pep_textbuf.h"
#include "pep_utf8.h"

static int parse_offset(const char *text, size_t *out)
{
    char *rest = nullptr;
    unsigned long value = strtoul(text, &rest, 10);
    if (rest == nullptr || *rest != '\0') {
        return 0;
    }
    *out = (size_t)value;
    return 1;
}

int main(int argc, char **argv)
{
    pep_textbuf_t bytes;
    size_t error_at = 0;
#ifdef _WIN32
    /* Byte-exact stdout: the suite asserts raw excerpt bytes including a
       lone CR. Test-driver-only; the library itself never touches modes. */
    (void)_setmode(_fileno(stdout), _O_BINARY);
#endif
    size_t arg;
    int status;
    (void)printf("n %d %d %d %d\n",
        pep_utf8_validate(nullptr, 1, nullptr),
        pep_span_locate(nullptr, 1, 0, nullptr, nullptr),
        pep_diag_render(nullptr, "f", "E", "m", nullptr, 0, 0),
        pep_textbuf_write(nullptr, stdout));
    if (argc < 5) {
        (void)fputs("usage: file_probe IN OUT LABEL OFF...\n", stderr);
        return 2;
    }
    if (pep_textbuf_init(&bytes) != 0) {
        return 1;
    }
    status = pep_textbuf_read_file(&bytes, argv[1]);
    if (status != 0) {
        (void)printf("r io\n");
        pep_textbuf_free(&bytes);
        return 1;
    }
    if (pep_utf8_validate(pep_textbuf_cstr(&bytes), pep_textbuf_len(&bytes), &error_at) == 0) {
        (void)printf("v ok\n");
    } else {
        (void)printf("v err %llu\n", (unsigned long long)error_at);
    }
    for (arg = 4; arg < (size_t)argc; arg++) {
        pep_textbuf_t diag;
        size_t off;
        if (!parse_offset(argv[arg], &off)) {
            pep_textbuf_free(&bytes);
            return 2;
        }
        if (pep_textbuf_init(&diag) != 0) {
            pep_textbuf_free(&bytes);
            return 1;
        }
        status = pep_diag_render(&diag, argv[3], "E_FILE", "file probe",
            pep_textbuf_cstr(&bytes), pep_textbuf_len(&bytes), off);
        if (status != 0) {
            pep_textbuf_free(&diag);
            pep_textbuf_free(&bytes);
            return 1;
        }
        status = pep_textbuf_write(&diag, stdout);
        pep_textbuf_free(&diag);
        if (status != 0) {
            pep_textbuf_free(&bytes);
            return 1;
        }
    }
    status = pep_textbuf_write_file(&bytes, argv[2]);
    if (status != 0) {
        (void)printf("w io\n");
        pep_textbuf_free(&bytes);
        return 1;
    }
    (void)printf("w ok %llu\n", (unsigned long long)pep_textbuf_len(&bytes));
    pep_textbuf_free(&bytes);
    return 0;
}
