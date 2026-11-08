// See pep_json.h for the contract. Strict C23, no extensions.
#include "pep_json.h"

static int append_short(pep_textbuf_t *buf, char one, char two)
{
    char pair[2];
    pair[0] = one;
    pair[1] = two;
    return pep_textbuf_append_bytes(buf, pair, 2);
}

int pep_json_escape(pep_textbuf_t *buf, const char *s, size_t n)
{
    static const char hex[] = "0123456789abcdef";
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
        } else if (c == '\n') {
            status = append_short(buf, '\\', 'n');
        } else if (c == '\r') {
            status = append_short(buf, '\\', 'r');
        } else if (c == '\t') {
            status = append_short(buf, '\\', 't');
        } else if (c == '\b') {
            status = append_short(buf, '\\', 'b');
        } else if (c == '\f') {
            status = append_short(buf, '\\', 'f');
        } else if (c < 0x20) {
            char uni[6];
            uni[0] = '\\';
            uni[1] = 'u';
            uni[2] = '0';
            uni[3] = '0';
            uni[4] = hex[(c >> 4) & 0xF];
            uni[5] = hex[c & 0xF];
            status = pep_textbuf_append_bytes(buf, uni, 6);
        } else {
            status = pep_textbuf_append_bytes(buf, &s[i], 1);
        }
        if (status != 0) {
            return status;
        }
    }
    return pep_textbuf_append_bytes(buf, "\"", 1);
}
