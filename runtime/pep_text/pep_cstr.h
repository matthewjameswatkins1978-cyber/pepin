// Agent-4 C literal emission: renders raw bytes as a C23 string literal
// the way a future native emitter must. Rules, chosen for safety on any
// conforming compiler and flags rather than brevity:
// - `"` -> `\"`, `\` -> `\\`, `?` -> `\?` (unconditional: no trigraph
//   can ever form, even under -trigraphs);
// - LF/TAB/CR/BEL/BS/FF/VT -> short escapes;
// - NUL, all other bytes below 0x20, DEL, and bytes above 0x7E ->
//   fixed 3-digit octal `\ooo` (never `\0` or short octal: a following
//   digit would merge into the escape and change the value);
// - printable ASCII otherwise passes through raw.
// The result always starts and ends with `"`. No validation: any bytes
// are literal content, exactly like the JSON escaper.
#ifndef PEP_CSTR_H
#define PEP_CSTR_H

#include <stddef.h>

#include "pep_textbuf.h"

// Append one C string literal for n raw bytes.
int pep_cstr_escape(pep_textbuf_t *buf, const char *s, size_t n);

#endif
