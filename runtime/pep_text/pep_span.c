// See pep_span.h for the contract. Strict C23, no extensions.
#include "pep_span.h"

int pep_span_locate(const char *s, size_t n, size_t offset,
                    unsigned long *line, unsigned long *col)
{
    unsigned long ln = 1;
    unsigned long cl = 1;
    size_t i;
    size_t stop;
    if (line == nullptr || col == nullptr) {
        return PEP_SPAN_BADARG;
    }
    if (s == nullptr && n != 0) {
        return PEP_SPAN_BADARG;
    }
    stop = (offset <= n) ? offset : n;
    for (i = 0; i < stop; i++) {
        if (s[i] == '\n') {
            ln += 1;
            cl = 1;
        } else {
            cl += 1;
        }
    }
    *line = ln;
    *col = cl;
    return PEP_SPAN_OK;
}

int pep_diag_render(pep_textbuf_t *buf, const char *file, const char *code,
                    const char *message, const char *s, size_t n, size_t offset)
{
    unsigned long line = 1;
    unsigned long col = 1;
    size_t start;
    size_t end;
    size_t i;
    int status;
    if (buf == nullptr || file == nullptr || code == nullptr || message == nullptr) {
        return PEP_SPAN_BADARG;
    }
    if (s == nullptr && n != 0) {
        return PEP_SPAN_BADARG;
    }
    if (offset > n) {
        offset = n;
    }
    status = pep_span_locate(s, n, offset, &line, &col);
    if (status != PEP_SPAN_OK) {
        return status;
    }
    status = pep_textbuf_append_cstr(buf, file);
    if (status != 0) {
        return status;
    }
    status = pep_textbuf_append_cstr(buf, ":");
    if (status != 0) {
        return status;
    }
    status = pep_textbuf_append_u64(buf, line);
    if (status != 0) {
        return status;
    }
    status = pep_textbuf_append_cstr(buf, ":");
    if (status != 0) {
        return status;
    }
    status = pep_textbuf_append_u64(buf, col);
    if (status != 0) {
        return status;
    }
    status = pep_textbuf_append_cstr(buf, ": ");
    if (status != 0) {
        return status;
    }
    status = pep_textbuf_append_cstr(buf, code);
    if (status != 0) {
        return status;
    }
    status = pep_textbuf_append_cstr(buf, ": ");
    if (status != 0) {
        return status;
    }
    status = pep_textbuf_append_cstr(buf, message);
    if (status != 0) {
        return status;
    }
    status = pep_textbuf_append_cstr(buf, "\n");
    if (status != 0) {
        return status;
    }
    // Excerpt: the line containing offset, without its '\n'.
    start = offset;
    while (start > 0 && s[start - 1] != '\n') {
        start -= 1;
    }
    end = offset;
    while (end < n && s[end] != '\n') {
        end += 1;
    }
    status = pep_textbuf_append_bytes(buf, s + start, end - start);
    if (status != 0) {
        return status;
    }
    status = pep_textbuf_append_cstr(buf, "\n");
    if (status != 0) {
        return status;
    }
    for (i = 1; i < col; i++) {
        status = pep_textbuf_append_cstr(buf, " ");
        if (status != 0) {
            return status;
        }
    }
    return pep_textbuf_append_cstr(buf, "^\n");
}
