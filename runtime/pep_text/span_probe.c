// Agent-4 span probe: renders one diagnostic block per requested offset.
// Usage: span_probe FILE LABEL OFFSET...  Each block is the exact bytes of
// pep_diag_render with code E_PROBE and message "probe message". The Python
// suite parses the first line of each block and checks line/column against
// the OCaml seed's inspect spans for the same file, and asserts full
// blocks for hand-computed excerpt/caret cases.
#include <stdio.h>

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif
#include <stdlib.h>
#include <string.h>

#include "pep_span.h"
#include "pep_textbuf.h"

int main(int argc, char **argv)
{
#ifdef _WIN32
    /* Byte-exact stdout: the suite asserts raw excerpt bytes including a
       lone CR. Test-driver-only; the library itself never touches modes. */
    (void)_setmode(_fileno(stdout), _O_BINARY);
#endif
    FILE *in;
    long file_len;
    char *bytes;
    size_t n;
    int arg;
    if (argc < 4) {
        (void)fputs("usage: span_probe FILE LABEL OFFSET...\n", stderr);
        return 2;
    }
    in = fopen(argv[1], "rb");
    if (in == nullptr) {
        (void)fputs("span_probe: cannot open input\n", stderr);
        return 2;
    }
    if (fseek(in, 0, SEEK_END) != 0) {
        (void)fclose(in);
        return 2;
    }
    file_len = ftell(in);
    if (file_len < 0) {
        (void)fclose(in);
        return 2;
    }
    if (fseek(in, 0, SEEK_SET) != 0) {
        (void)fclose(in);
        return 2;
    }
    n = (size_t)file_len;
    bytes = (char *)malloc(n > 0 ? n : 1);
    if (bytes == nullptr) {
        (void)fclose(in);
        return 2;
    }
    if (n > 0 && fread(bytes, 1, n, in) != n) {
        free(bytes);
        (void)fclose(in);
        return 2;
    }
    (void)fclose(in);
    for (arg = 3; arg < argc; arg++) {
        pep_textbuf_t buf;
        char *rest = nullptr;
        unsigned long off = strtoul(argv[arg], &rest, 10);
        if (rest == nullptr || *rest != '\0') {
            free(bytes);
            return 2;
        }
        if (pep_textbuf_init(&buf) != 0) {
            free(bytes);
            return 1;
        }
        if (pep_diag_render(&buf, argv[2], "E_PROBE", "probe message",
                            bytes, n, (size_t)off) != 0) {
            pep_textbuf_free(&buf);
            free(bytes);
            return 1;
        }
        if (pep_textbuf_write(&buf, stdout) != 0) {
            pep_textbuf_free(&buf);
            free(bytes);
            return 1;
        }
        pep_textbuf_free(&buf);
    }
    free(bytes);
    return 0;
}
