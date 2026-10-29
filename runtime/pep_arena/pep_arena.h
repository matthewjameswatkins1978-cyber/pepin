// Agent-4 native AST arena: explicit-lifetime, chunked, growable storage
// for one compilation operation's temporary recursive data (AST nodes,
// node lists, scratch trees). The arena owns BYTES only: what those bytes
// mean — tags, child counts, unions, type facts — stays with Pep and the
// checker. An arena is an explicit-lifetime storage mechanism, not a
// language-wide GC decision, and it never overrides ownership checks.
//
// Contract highlights (full rules below):
// - Opaque handle; `init` allocates it, `free` releases everything.
// - Chunks are never moved or reallocated, so every returned pointer
//   stays valid until `pep_arena_free`.
// - Checked sizes and power-of-two alignment; overflow and allocation
//   failure surface as sticky codes, never as wrapped sizes or NULL
//   dereferences. Callers MUST null-check every allocation.
// - No global state, no thread-safety claims (single-threaded use;
//   one arena per compilation unit is the intended shape).
#ifndef PEP_ARENA_H
#define PEP_ARENA_H

#include <stddef.h>

typedef struct pep_arena pep_arena_t;

enum {
    PEP_ARENA_OK = 0,       // healthy; allocations succeed
    PEP_ARENA_ALLOC = 1,    // host allocation (chunk) refused; old bytes intact
    PEP_ARENA_OVERFLOW = 2, // size/alignment math cannot be satisfied
    PEP_ARENA_BADARG = 3    // null handle, zero size, or non-power-of-two alignment
};

// Initialise an empty arena. `chunk_hint` is the first chunk's usable
// capacity in bytes; 0 selects a small default. The handle itself is
// heap-allocated: on failure `*arena` is NULL and the result is
// PEP_ARENA_ALLOC. Never returns a partially built arena.
int pep_arena_init(pep_arena_t **arena, size_t chunk_hint);

// Allocate `size` bytes with `align` alignment from the arena's current
// chunk, growing by a new chunk when the remainder does not fit.
// `size` must be non-zero and `align` a non-zero power of two.
// Returns NULL on any failure or bad argument AND records a sticky
// error (see pep_arena_status): a stale arena keeps failing closed
// instead of handing out overlapping memory.
void *pep_arena_alloc(pep_arena_t *arena, size_t size, size_t align);

// Read the sticky status: PEP_ARENA_OK while healthy, otherwise the
// first failure code. Passing NULL reports PEP_ARENA_BADARG.
int pep_arena_status(const pep_arena_t *arena);

// Release every chunk and the handle itself, then set `*arena` to NULL.
// Safe on a NULL argument, a NULL handle, and repeated calls.
void pep_arena_free(pep_arena_t **arena);

#endif
