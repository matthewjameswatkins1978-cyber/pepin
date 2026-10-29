// See pep_jsonval.h for the contract. Strict C23, no extensions.
#include "pep_jsonval.h"

int pep_json_begin_object(pep_textbuf_t *buf)
{
    if (buf == nullptr) {
        return PEP_TEXTBUF_BADARG;
    }
    return pep_textbuf_append_bytes(buf, "{", 1);
}

int pep_json_end_object(pep_textbuf_t *buf)
{
    if (buf == nullptr) {
        return PEP_TEXTBUF_BADARG;
    }
    return pep_textbuf_append_bytes(buf, "}", 1);
}

int pep_json_begin_array(pep_textbuf_t *buf)
{
    if (buf == nullptr) {
        return PEP_TEXTBUF_BADARG;
    }
    return pep_textbuf_append_bytes(buf, "[", 1);
}

int pep_json_end_array(pep_textbuf_t *buf)
{
    if (buf == nullptr) {
        return PEP_TEXTBUF_BADARG;
    }
    return pep_textbuf_append_bytes(buf, "]", 1);
}

int pep_json_comma(pep_textbuf_t *buf)
{
    if (buf == nullptr) {
        return PEP_TEXTBUF_BADARG;
    }
    return pep_textbuf_append_bytes(buf, ",", 1);
}

int pep_json_colon(pep_textbuf_t *buf)
{
    if (buf == nullptr) {
        return PEP_TEXTBUF_BADARG;
    }
    return pep_textbuf_append_bytes(buf, ":", 1);
}

int pep_json_str(pep_textbuf_t *buf, const char *s, size_t n)
{
    if (buf == nullptr) {
        return PEP_TEXTBUF_BADARG;
    }
    return pep_json_escape(buf, s, n);
}

int pep_json_int(pep_textbuf_t *buf, long long value)
{
    if (buf == nullptr) {
        return PEP_TEXTBUF_BADARG;
    }
    return pep_textbuf_append_i64(buf, value);
}

int pep_json_bool(pep_textbuf_t *buf, int value)
{
    if (buf == nullptr) {
        return PEP_TEXTBUF_BADARG;
    }
    return pep_textbuf_append_cstr(buf, value ? "true" : "false");
}

int pep_json_null(pep_textbuf_t *buf)
{
    if (buf == nullptr) {
        return PEP_TEXTBUF_BADARG;
    }
    return pep_textbuf_append_cstr(buf, "null");
}

int pep_json_key(pep_textbuf_t *buf, const char *s, size_t n)
{
    int status;
    if (buf == nullptr) {
        return PEP_TEXTBUF_BADARG;
    }
    status = pep_json_escape(buf, s, n);
    if (status != 0) {
        return status;
    }
    return pep_textbuf_append_bytes(buf, ":", 1);
}
