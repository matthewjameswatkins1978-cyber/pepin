// Agent-4 length-tagged fragment probe: joins explicit byte slices of a
// file with pep_textbuf_join_n, preserving embedded NUL bytes.
// Usage: fragn_probe FILE OFF LEN [OFF LEN]... Each slice is the half-open
// range [OFF, OFF+LEN); all slices are joined in one call and the result
// goes to stdout. Bad numbers or out-of-range slices fail closed before
// anything is written (exit 2). Binary stdout (see span_probe) so
// asserted bytes are exact. Companion to frag_probe, which covers
// NUL-terminated fragments.
#include <stdio.h>
#include <stdlib.h>

#include "pep_textbuf.h"

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

static int parse_number(const char *text, size_t *out)
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
    FILE *in;
    long file_len;
    char *bytes;
    size_t n;
    size_t pairs;
    size_t i;
    const char **parts;
    size_t *lens;
    pep_textbuf_t buf;
    int status;
#ifdef _WIN32
    (void)_setmode(_fileno(stdout), _O_BINARY);
#endif
    if (argc < 2 || ((argc - 2) % 2) != 0) {
        (void)fputs("usage: fragn_probe FILE [OFF LEN]...\n", stderr);
        return 2;
    }
    in = fopen(argv[1], "rb");
    if (in == nullptr) {
        (void)fputs("fragn_probe: cannot open input\n", stderr);
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
    pairs = (size_t)(argc - 2) / 2;
    parts = (const char **)malloc(pairs > 0 ? pairs * sizeof *parts : 1);
    lens = (size_t *)malloc(pairs > 0 ? pairs * sizeof *lens : 1);
    if ((pairs > 0 && (parts == nullptr || lens == nullptr))) {
        free(lens);
        free(parts);
        free(bytes);
        return 2;
    }
    for (i = 0; i < pairs; i++) {
        size_t off = 0;
        size_t len = 0;
        if (!parse_number(argv[2 + i * 2], &off) || !parse_number(argv[2 + i * 2 + 1], &len)) {
            free(lens);
            free(parts);
            free(bytes);
            return 2;
        }
        if (off > n || len > n - off) {
            free(lens);
            free(parts);
            free(bytes);
            return 2;
        }
        parts[i] = bytes + off;
        lens[i] = len;
    }
    if (pep_textbuf_init(&buf) != 0) {
        free(lens);
        free(parts);
        free(bytes);
        return 1;
    }
    status = pep_textbuf_join_n(&buf, parts, lens, pairs);
    free(lens);
    free(parts);
    free(bytes);
    if (status != 0) {
        pep_textbuf_free(&buf);
        return 1;
    }
    status = pep_textbuf_write(&buf, stdout);
    pep_textbuf_free(&buf);
    return (status == 0) ? 0 : 1;
}
