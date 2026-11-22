#include "pep_textbuf.h"

#include <assert.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>

static size_t reallocations;
static bool refuse;

void *probe_realloc(void *ptr, size_t size)
{
    reallocations++;
    return refuse ? nullptr : realloc(ptr, size);
}

int main(void)
{
    const char expected[] = "prefix\0" "0 -1 -9223372036854775808 18446744073709551615";
    const char prefix[] = "prefix";
    pep_textbuf_t buf;
    assert(pep_textbuf_init(&buf) == PEP_TEXTBUF_OK);
    // Include a meaningful NUL byte before the decimal fragments.
    assert(pep_textbuf_append_bytes(&buf, prefix, sizeof prefix) == PEP_TEXTBUF_OK);
    assert(pep_textbuf_append_u64(&buf, 0) == PEP_TEXTBUF_OK);
    assert(pep_textbuf_append_bytes(&buf, " ", 1) == PEP_TEXTBUF_OK);
    assert(pep_textbuf_append_i64(&buf, -1) == PEP_TEXTBUF_OK);
    assert(pep_textbuf_append_bytes(&buf, " ", 1) == PEP_TEXTBUF_OK);
    size_t before = reallocations;
    assert(pep_textbuf_append_i64(&buf, -9223372036854775807LL - 1) == PEP_TEXTBUF_OK);
    assert(reallocations == before + 1);
    assert(pep_textbuf_append_bytes(&buf, " ", 1) == PEP_TEXTBUF_OK);
    assert(pep_textbuf_append_u64(&buf, 18446744073709551615ULL) == PEP_TEXTBUF_OK);
    assert(pep_textbuf_len(&buf) == sizeof expected - 1);
    assert(memcmp(pep_textbuf_cstr(&buf), expected, sizeof expected) == 0);
    pep_textbuf_free(&buf);

    const char old[] = "1234";
    assert(pep_textbuf_init(&buf) == PEP_TEXTBUF_OK);
    assert(pep_textbuf_append_bytes(&buf, old, sizeof old - 1) == PEP_TEXTBUF_OK);
    refuse = true;
    before = reallocations;
    assert(pep_textbuf_append_i64(&buf, LLONG_MIN) == PEP_TEXTBUF_ALLOC);
    assert(pep_textbuf_len(&buf) == sizeof old - 1);
    assert(memcmp(pep_textbuf_cstr(&buf), old, sizeof old) == 0);
    assert(pep_textbuf_append_u64(&buf, ULLONG_MAX) == PEP_TEXTBUF_ALLOC);
    assert(reallocations == before + 1);
    pep_textbuf_free(&buf);
}
