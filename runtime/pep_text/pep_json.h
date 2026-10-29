// Agent-4 JSON string escaping: byte-exact mirror of the OCaml seed's
// `json_string` (pep_ocaml.ml), the function behind every machine-readable
// string in inspect/check/query output. Pep cannot express this: Str has
// no byte access and no concatenation in the language, so the bytes live
// here. A future native machine interface can reuse this without touching
// the semantic authority: escaping changes no meaning, only rendering.
#ifndef PEP_JSON_H
#define PEP_JSON_H

#include <stddef.h>

#include "pep_textbuf.h"

// Append one JSON string literal for n raw bytes: opening quote, escaped
// content, closing quote. Mapping matches the seed exactly:
// `"` -> `\"`, `\` -> `\\`, LF/CR/TAB/BS/FF -> short escapes, other bytes
// below 0x20 -> `\u00xx` (lowercase), everything else passes through raw
// (including DEL, UTF-8, and invalid bytes — the seed does not validate).
int pep_json_escape(pep_textbuf_t *buf, const char *s, size_t n);

#endif
