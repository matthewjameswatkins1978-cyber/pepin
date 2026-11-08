// See pep_cstr.h for the contract. Strict C23, no extensions.
#include "pep_cstr.h"

static int append_short(pep_textbuf_t *buf, char one, char two)
{
    char pair[2];
    pair[0] = one;
    pair[1] = two;
    return pep_textbuf_append_bytes(buf, pair, 2);
}

int pep_cstr_escape(pep_textbuf_t *buf, const char *s, size_t n)
{
    static const char oct[] = "01234567";
    size_t i;
    int status;
    if (buf == nullptr || (s == nullptr && n != 0)) {
        return PEP_TEXTBUF_BADARG;
    }
    status = pep_textbuf_append_bytes(buf, "\"", 1);
    if (status != 0) {
        return status;
    }
    for (i = 0; i < n; i++) {
        unsigned char c = (unsigned char)s[i];
        if (c == '"') {
            status = append_short(buf, '\\', '"');
        } else if (c == '\\') {
            status = append_short(buf, '\\', '\\');
        } else if (c == '?') {
            status = append_short(buf, '\\', '?');
        } else if (c == '\n') {
            status = append_short(buf, '\\', 'n');
        } else if (c == '\t') {
            status = append_short(buf, '\\', 't');
        } else if (c == '\r') {
            status = append_short(buf, '\\', 'r');
        } else if (c == '\a') {
            status = append_short(buf, '\\', 'a');
        } else if (c == '\b') {
            status = append_short(buf, '\\', 'b');
        } else if (c == '\f') {
            status = append_short(buf, '\\', 'f');
        } else if (c == '\v') {
            status = append_short(buf, '\\', 'v');
        } else if (c >= 0x20 && c <= 0x7E) {
            status = pep_textbuf_append_bytes(buf, &s[i], 1);
        } else {
            char esc[4];
            esc[0] = '\\';
            esc[1] = oct[(c >> 6) & 0x7];
            esc[2] = oct[(c >> 3) & 0x7];
            esc[3] = oct[c & 0x7];
            status = pep_textbuf_append_bytes(buf, esc, 4);
        }
        if (status != 0) {
            return status;
        }
    }
    return pep_textbuf_append_bytes(buf, "\"", 1);
}
