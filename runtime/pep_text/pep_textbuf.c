// See pep_textbuf.h for the contract. Strict C23, no extensions.
#include "pep_textbuf.h"

#include <stdlib.h>
#include <string.h>

#define PEP_TEXTBUF_FLOOR ((size_t)8)

static int note(pep_textbuf_t *buf, int code)
{
    if (buf->err == PEP_TEXTBUF_OK) {
        buf->err = code;
    }
    return code;
}

// Saturating double shared with the Pep model (grow_step): doubling stops
// at SIZE_MAX instead of wrapping. Returns false when `need` itself cannot
// be represented alongside the terminator.
static bool next_capacity(size_t cap, size_t need, size_t *out)
{
    size_t step;
    if (cap == 0) {
        step = PEP_TEXTBUF_FLOOR;
    } else if (cap > SIZE_MAX / 2) {
        step = SIZE_MAX;
    } else {
        step = cap * 2;
    }
    if (step < PEP_TEXTBUF_FLOOR) {
        step = PEP_TEXTBUF_FLOOR;
    }
    if (step < need) {
        step = need;
    }
    *out = step;
    return true;
}

int pep_textbuf_init(pep_textbuf_t *buf)
{
    if (buf == nullptr) {
        return PEP_TEXTBUF_BADARG;
    }
    buf->data = nullptr;
    buf->len = 0;
    buf->cap = 0;
    buf->err = PEP_TEXTBUF_OK;
    return PEP_TEXTBUF_OK;
}

int pep_textbuf_reserve(pep_textbuf_t *buf, size_t extra)
{
    size_t need;
    size_t want;
    char *grown;
    if (buf == nullptr) {
        return PEP_TEXTBUF_BADARG;
    }
    if (buf->err != PEP_TEXTBUF_OK) {
        return buf->err;
    }
    if (extra > SIZE_MAX - buf->len - 1) {
        return note(buf, PEP_TEXTBUF_OVERFLOW);
    }
    need = buf->len + extra + 1;
    if (need <= buf->cap) {
        return PEP_TEXTBUF_OK;
    }
    (void)next_capacity(buf->cap, need, &want);
    grown = (char *)realloc(buf->data, want);
    if (grown == nullptr) {
        return note(buf, PEP_TEXTBUF_ALLOC);
    }
    buf->data = grown;
    buf->cap = want;
    buf->data[buf->len] = '\0';
    return PEP_TEXTBUF_OK;
}

int pep_textbuf_append_bytes(pep_textbuf_t *buf, const char *src, size_t n)
{
    int status;
    if (buf == nullptr || (src == nullptr && n != 0)) {
        return PEP_TEXTBUF_BADARG;
    }
    status = pep_textbuf_reserve(buf, n);
    if (status != PEP_TEXTBUF_OK) {
        return status;
    }
    if (n != 0) {
        memcpy(buf->data + buf->len, src, n);
        buf->len += n;
        buf->data[buf->len] = '\0';
    }
    return PEP_TEXTBUF_OK;
}

int pep_textbuf_append_cstr(pep_textbuf_t *buf, const char *s)
{
    if (s == nullptr) {
        return PEP_TEXTBUF_BADARG;
    }
    return pep_textbuf_append_bytes(buf, s, strlen(s));
}

int pep_textbuf_append_u64(pep_textbuf_t *buf, unsigned long long value)
{
    char digits[20];
    size_t count = 0;
    size_t i;
    if (buf == nullptr) {
        return PEP_TEXTBUF_BADARG;
    }
    do {
        digits[count] = (char)('0' + value % 10);
        count++;
        value /= 10;
    } while (value != 0);
    for (i = 0; i < count; i++) {
        int status = pep_textbuf_append_bytes(buf, &digits[count - 1 - i], 1);
        if (status != PEP_TEXTBUF_OK) {
            return status;
        }
    }
    return PEP_TEXTBUF_OK;
}

int pep_textbuf_append_i64(pep_textbuf_t *buf, long long value)
{
    unsigned long long mag;
    if (buf == nullptr) {
        return PEP_TEXTBUF_BADARG;
    }
    if (value < 0) {
        int status = pep_textbuf_append_bytes(buf, "-", 1);
        if (status != PEP_TEXTBUF_OK) {
            return status;
        }
        // Negating INT64_MIN is undefined; convert via unsigned arithmetic.
        mag = (unsigned long long)(-(value + 1)) + 1u;
    } else {
        mag = (unsigned long long)value;
    }
    return pep_textbuf_append_u64(buf, mag);
}

int pep_textbuf_join(pep_textbuf_t *buf, const char *const *parts, size_t count)
{
    size_t i;
    if (buf == nullptr) {
        return PEP_TEXTBUF_BADARG;
    }
    if (parts == nullptr && count != 0) {
        return note(buf, PEP_TEXTBUF_BADARG);
    }
    for (i = 0; i < count; i++) {
        int status;
        if (parts[i] == nullptr) {
            return note(buf, PEP_TEXTBUF_BADARG);
        }
        status = pep_textbuf_append_cstr(buf, parts[i]);
        if (status != PEP_TEXTBUF_OK) {
            return status;
        }
    }
    return buf->err;
}

const char *pep_textbuf_cstr(const pep_textbuf_t *buf)
{
    if (buf == nullptr || buf->data == nullptr) {
        return "";
    }
    return buf->data;
}

size_t pep_textbuf_len(const pep_textbuf_t *buf)
{
    if (buf == nullptr) {
        return 0;
    }
    return buf->len;
}

int pep_textbuf_write(const pep_textbuf_t *buf, FILE *out)
{
    if (buf == nullptr || out == nullptr) {
        return PEP_TEXTBUF_BADARG;
    }
    if (buf->err != PEP_TEXTBUF_OK) {
        return buf->err;
    }
    if (buf->len != 0) {
        if (fwrite(buf->data, 1, buf->len, out) != buf->len) {
            return PEP_TEXTBUF_IO;
        }
    }
    return PEP_TEXTBUF_OK;
}

void pep_textbuf_free(pep_textbuf_t *buf)
{
    if (buf == nullptr) {
        return;
    }
    free(buf->data);
    buf->data = nullptr;
    buf->len = 0;
    buf->cap = 0;
    buf->err = PEP_TEXTBUF_OK;
}
