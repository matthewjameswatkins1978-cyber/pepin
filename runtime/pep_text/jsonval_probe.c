// Agent-4 JSON value probe: emits one fixed nested document shaped like
// a tiny compiler report, exercising every writer including empty
// object/array, escapes, unicode, booleans, null, and INT64_MIN.
// Prints the document plus '\n'. Binary stdout (see span_probe).
#include <stdio.h>

#include "pep_jsonval.h"
#include "pep_textbuf.h"

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

#define CHECK(call) do { if ((call) != 0) { pep_textbuf_free(&buf); return 1; } } while (0)

int main(void)
{
    pep_textbuf_t buf;
    static const char note[] = "caf\xC3\xA9 \"x\"\n";
#ifdef _WIN32
    (void)_setmode(_fileno(stdout), _O_BINARY);
#endif
    if (pep_textbuf_init(&buf) != 0) {
        return 1;
    }
    CHECK(pep_json_begin_object(&buf));
    CHECK(pep_json_key(&buf, "schemaVersion", 13));
    CHECK(pep_json_int(&buf, 2));
    CHECK(pep_json_comma(&buf));
    CHECK(pep_json_key(&buf, "status", 6));
    CHECK(pep_json_str(&buf, "parsed", 6));
    CHECK(pep_json_comma(&buf));
    CHECK(pep_json_key(&buf, "ast", 3));
    CHECK(pep_json_begin_array(&buf));
    CHECK(pep_json_begin_object(&buf));
    CHECK(pep_json_key(&buf, "kind", 4));
    CHECK(pep_json_str(&buf, "function", 8));
    CHECK(pep_json_comma(&buf));
    CHECK(pep_json_key(&buf, "name", 4));
    CHECK(pep_json_str(&buf, "main", 4));
    CHECK(pep_json_comma(&buf));
    CHECK(pep_json_key(&buf, "ok", 2));
    CHECK(pep_json_bool(&buf, 1));
    CHECK(pep_json_comma(&buf));
    CHECK(pep_json_key(&buf, "value", 5));
    CHECK(pep_json_int(&buf, 42));
    CHECK(pep_json_comma(&buf));
    CHECK(pep_json_key(&buf, "big", 3));
    CHECK(pep_json_int(&buf, (-9223372036854775807LL - 1)));
    CHECK(pep_json_comma(&buf));
    CHECK(pep_json_key(&buf, "missing", 7));
    CHECK(pep_json_null(&buf));
    CHECK(pep_json_comma(&buf));
    CHECK(pep_json_key(&buf, "tags", 4));
    CHECK(pep_json_begin_array(&buf));
    CHECK(pep_json_end_array(&buf));
    CHECK(pep_json_end_object(&buf));
    CHECK(pep_json_end_array(&buf));
    CHECK(pep_json_comma(&buf));
    CHECK(pep_json_key(&buf, "empty", 5));
    CHECK(pep_json_begin_object(&buf));
    CHECK(pep_json_end_object(&buf));
    CHECK(pep_json_comma(&buf));
    CHECK(pep_json_key(&buf, "note", 4));
    CHECK(pep_json_str(&buf, note, sizeof note - 1));
    CHECK(pep_json_end_object(&buf));
    CHECK(pep_textbuf_append_bytes(&buf, "\n", 1));
    CHECK(pep_textbuf_write(&buf, stdout));
    pep_textbuf_free(&buf);
    return 0;
}
