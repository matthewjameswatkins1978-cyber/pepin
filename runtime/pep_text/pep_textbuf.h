// Agent-4 native text/byte builder: minimal C23 runtime primitive.
//
// Pep cannot yet express raw bytes, allocation, or Str concatenation, so
// storage, growth looping, integer formatting, and joining live here. The
// growth *policy* (saturating double, floor of 8) is mirrored in Pep in
// pep_textbuf_core.pep / pep_textbuf_model.pep; this file owns only the
// byte mechanics. No Pep language semantics live here.
//
// Contract: every function returns an int status (0 ok). On allocation
// failure the buffer keeps its previous bytes valid and records the error;
// the caller must still call pep_textbuf_free. Sizes are size_t; any
// request that cannot be represented fails with PEP_TEXTBUF_OVERFLOW and
// never wraps around.
#ifndef PEP_TEXTBUF_H
#define PEP_TEXTBUF_H

#include <stddef.h>
#include <stdio.h>

typedef struct {
    char *data;    // owned heap bytes, always NUL-terminated when cap > 0
    size_t len;    // used bytes, not counting the terminator
    size_t cap;    // allocated bytes including room for the terminator
    int err;       // first sticky error, PEP_TEXTBUF_* below
} pep_textbuf_t;

enum {
    PEP_TEXTBUF_OK = 0,
    PEP_TEXTBUF_ALLOC = 1,    // malloc/realloc refused; old bytes intact
    PEP_TEXTBUF_OVERFLOW = 2, // size cannot be represented; nothing changed
    PEP_TEXTBUF_BADARG = 3,   // null pointer argument
    PEP_TEXTBUF_IO = 4        // output stream reported an error
};

// Initialise an empty builder. Fails only on a null argument.
int pep_textbuf_init(pep_textbuf_t *buf);

// Ensure room for `extra` more bytes plus the terminator, growing by the
// saturating-double policy shared with the Pep model. Never shrinks.
int pep_textbuf_reserve(pep_textbuf_t *buf, size_t extra);

// Append raw bytes / a NUL-terminated string / a signed 64-bit integer in
// decimal (INT64_MIN safe) / an unsigned 64-bit integer in decimal.
int pep_textbuf_append_bytes(pep_textbuf_t *buf, const char *src, size_t n);
int pep_textbuf_append_cstr(pep_textbuf_t *buf, const char *s);
int pep_textbuf_append_i64(pep_textbuf_t *buf, long long value);
int pep_textbuf_append_u64(pep_textbuf_t *buf, unsigned long long value);

// Join helper for a host-owned fragment list (see INTEGRATION.md): appends
// `count` NUL-terminated fragments in order. Replaces the Python-side
// "".join once the differential gate passes; Python remains the authority
// until then.
int pep_textbuf_join(pep_textbuf_t *buf, const char *const *parts, size_t count);

// Read-only views. cstr is valid until the next mutating call or free;
// it is "" when the builder never successfully allocated.
const char *pep_textbuf_cstr(const pep_textbuf_t *buf);
size_t pep_textbuf_len(const pep_textbuf_t *buf);

// Write the used bytes to `out`. Reports PEP_TEXTBUF_IO on stream errors.
int pep_textbuf_write(const pep_textbuf_t *buf, FILE *out);

// Read an entire file's bytes into the builder (binary, no translation).
// Missing files and read/close errors report PEP_TEXTBUF_IO; bytes read
// before a mid-stream failure stay in the builder with a sticky error.
int pep_textbuf_read_file(pep_textbuf_t *buf, const char *path);

// Write the used bytes to a file (binary, created or truncated).
int pep_textbuf_write_file(const pep_textbuf_t *buf, const char *path);

// Release ownership; safe on a zeroed, moved, or partially built buffer.
void pep_textbuf_free(pep_textbuf_t *buf);

#endif
