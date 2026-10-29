// See pep_arena.h for the contract. Strict C23, no extensions.
// Chunks are single-linked and never moved: pointers stay valid for
// the arena's lifetime. All size math is checked before use; nothing
// here can wrap around or read out of bounds on conforming input.
#include "pep_arena.h"

#include <stdint.h>
#include <stdlib.h>

#define PEP_ARENA_DEFAULT_CHUNK ((size_t)4096)

struct pep_chunk {
    struct pep_chunk *next;
    size_t cap;   // usable bytes in data[] (invariant: used <= cap)
    size_t used;  // bytes handed out so far, including padding
    unsigned char data[];
};

struct pep_arena {
    struct pep_chunk *head;
    struct pep_chunk *tail;
    size_t next_cap; // growth target for the next fresh chunk
    int err;         // first sticky failure code
};

static int is_pow2(size_t alignment)
{
    return alignment != 0 && (alignment & (alignment - 1)) == 0;
}

static int note(pep_arena_t *arena, int code)
{
    if (arena->err == PEP_ARENA_OK) {
        arena->err = code;
    }
    return code;
}

int pep_arena_init(pep_arena_t **arena, size_t chunk_hint)
{
    pep_arena_t *fresh;
    if (arena == nullptr) {
        return PEP_ARENA_BADARG;
    }
    fresh = (pep_arena_t *)malloc(sizeof *fresh);
    if (fresh == nullptr) {
        *arena = nullptr;
        return PEP_ARENA_ALLOC;
    }
    fresh->head = nullptr;
    fresh->tail = nullptr;
    fresh->next_cap = (chunk_hint == 0) ? PEP_ARENA_DEFAULT_CHUNK : chunk_hint;
    fresh->err = PEP_ARENA_OK;
    *arena = fresh;
    return PEP_ARENA_OK;
}

// Allocate one fresh chunk holding at least `need` usable bytes and
// hand out its first `size` bytes at `align` from the chunk start.
static void *grow(pep_arena_t *arena, size_t size, size_t align)
{
    size_t grown;
    size_t cap;
    size_t total;
    struct pep_chunk *fresh;
    uintptr_t base;
    uintptr_t cur;
    size_t pad;
    if (align - 1 > SIZE_MAX - size) {
        (void)note(arena, PEP_ARENA_OVERFLOW);
        return nullptr;
    }
    grown = arena->next_cap;
    if (grown <= SIZE_MAX / 2) {
        grown *= 2;
    } else {
        grown = SIZE_MAX;
    }
    {
        size_t need = size + (align - 1);
        cap = (need > grown) ? need : grown;
    }
    arena->next_cap = grown;
    if (cap > SIZE_MAX - sizeof(struct pep_chunk)) {
        (void)note(arena, PEP_ARENA_OVERFLOW);
        return nullptr;
    }
    total = sizeof(struct pep_chunk) + cap;
    fresh = (struct pep_chunk *)malloc(total);
    if (fresh == nullptr) {
        (void)note(arena, PEP_ARENA_ALLOC);
        return nullptr;
    }
    fresh->next = nullptr;
    fresh->cap = cap;
    base = (uintptr_t)(fresh->data);
    pad = (align - (base % align)) % align;
    fresh->used = pad + size;
    if (arena->tail == nullptr) {
        arena->head = fresh;
    } else {
        arena->tail->next = fresh;
    }
    arena->tail = fresh;
    cur = base + pad;
    return (void *)cur;
}

void *pep_arena_alloc(pep_arena_t *arena, size_t size, size_t align)
{
    uintptr_t base;
    uintptr_t cur;
    size_t pad;
    size_t rest;
    if (arena == nullptr) {
        return nullptr;
    }
    if (size == 0 || !is_pow2(align)) {
        (void)note(arena, PEP_ARENA_BADARG);
        return nullptr;
    }
    if (arena->err != PEP_ARENA_OK) {
        return nullptr;
    }
    if (arena->tail != nullptr) {
        base = (uintptr_t)(arena->tail->data);
        cur = base + arena->tail->used;
        pad = (align - (cur % align)) % align;
        // used <= cap always holds, so these subtractions cannot wrap.
        if (pad <= arena->tail->cap - arena->tail->used) {
            rest = arena->tail->cap - arena->tail->used - pad;
            if (size <= rest) {
                arena->tail->used += pad + size;
                return (void *)(cur + pad);
            }
        }
    }
    return grow(arena, size, align);
}

int pep_arena_status(const pep_arena_t *arena)
{
    if (arena == nullptr) {
        return PEP_ARENA_BADARG;
    }
    return arena->err;
}

void pep_arena_free(pep_arena_t **arena)
{
    if (arena != nullptr && *arena != nullptr) {
        struct pep_chunk *chunk = (*arena)->head;
        while (chunk != nullptr) {
            struct pep_chunk *next = chunk->next;
            free(chunk);
            chunk = next;
        }
        free(*arena);
        *arena = nullptr;
    }
}
