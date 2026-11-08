// Agent-4 JSON probe: escapes one file's raw bytes as a single JSON
// string literal. Usage: json_probe FILE. Prints the literal plus '\n'.
// Binary stdout (see span_probe) so asserted bytes are exact on Windows.
#include <stdio.h>
#include <stdlib.h>

#include "pep_json.h"
#include "pep_textbuf.h"

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

int main(int argc, char **argv)
{
    FILE *in;
    long file_len;
    char *bytes;
    size_t n;
    pep_textbuf_t buf;
    int status;
#ifdef _WIN32
    (void)_setmode(_fileno(stdout), _O_BINARY);
#endif
    if (argc != 2) {
        (void)fputs("usage: json_probe FILE\n", stderr);
        return 2;
    }
    in = fopen(argv[1], "rb");
    if (in == nullptr) {
        (void)fputs("json_probe: cannot open input\n", stderr);
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
    if (pep_textbuf_init(&buf) != 0) {
        free(bytes);
        return 1;
    }
    status = pep_json_escape(&buf, bytes, n);
    free(bytes);
    if (status != 0) {
        pep_textbuf_free(&buf);
        return 1;
    }
    status = pep_textbuf_append_bytes(&buf, "\n", 1);
    if (status != 0) {
        pep_textbuf_free(&buf);
        return 1;
    }
    status = pep_textbuf_write(&buf, stdout);
    pep_textbuf_free(&buf);
    return (status == 0) ? 0 : 1;
}
