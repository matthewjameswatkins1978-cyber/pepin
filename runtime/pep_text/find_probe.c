// Agent-4 find probe: searches each NEEDLE file's whole contents in the
// HAYSTACK file with pep_text_find. Usage: find_probe HAYSTACK NEEDLE...
// Prints one line per needle: `f OFFSET` or `f none`. Empty needle files
// match at 0; embedded NULs are ordinary bytes on both sides. Binary
// stdout (see span_probe) so asserted bytes are exact. Missing or
// unreadable inputs exit 2 before anything prints.
#include <stdio.h>
#include <stdlib.h>

#include "pep_find.h"
#include "pep_textbuf.h"

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

static int read_whole(const char *path, char **out_bytes, size_t *out_n)
{
    FILE *in = fopen(path, "rb");
    long file_len;
    char *bytes;
    if (in == nullptr) {
        return 1;
    }
    if (fseek(in, 0, SEEK_END) != 0) {
        (void)fclose(in);
        return 1;
    }
    file_len = ftell(in);
    if (file_len < 0) {
        (void)fclose(in);
        return 1;
    }
    if (fseek(in, 0, SEEK_SET) != 0) {
        (void)fclose(in);
        return 1;
    }
    *out_n = (size_t)file_len;
    bytes = (char *)malloc(*out_n > 0 ? *out_n : 1);
    if (bytes == nullptr) {
        (void)fclose(in);
        return 1;
    }
    if (*out_n > 0 && fread(bytes, 1, *out_n, in) != *out_n) {
        free(bytes);
        (void)fclose(in);
        return 1;
    }
    (void)fclose(in);
    *out_bytes = bytes;
    return 0;
}

int main(int argc, char **argv)
{
    char *hay = nullptr;
    size_t hn = 0;
    int arg;
#ifdef _WIN32
    (void)_setmode(_fileno(stdout), _O_BINARY);
#endif
    if (argc < 3) {
        (void)fputs("usage: find_probe HAYSTACK NEEDLE...\n", stderr);
        return 2;
    }
    if (read_whole(argv[1], &hay, &hn) != 0) {
        return 2;
    }
    for (arg = 2; arg < argc; arg++) {
        char *ndl = nullptr;
        size_t nn = 0;
        size_t at = 0;
        int status;
        if (read_whole(argv[arg], &ndl, &nn) != 0) {
            free(hay);
            return 2;
        }
        status = pep_text_find(hay, hn, ndl, nn, &at);
        free(ndl);
        if (status == PEP_FIND_OK) {
            (void)printf("f %llu\n", (unsigned long long)at);
        } else if (status == PEP_FIND_NONE) {
            (void)printf("f none\n");
        } else {
            free(hay);
            return 1;
        }
    }
    free(hay);
    return 0;
}
