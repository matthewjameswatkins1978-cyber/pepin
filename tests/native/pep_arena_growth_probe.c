#include "pep_arena.h"

#include <assert.h>
#include <stdlib.h>

static size_t attempts;

// Only the arena translation unit uses these allocator overrides.
void *probe_malloc(size_t size)
{
    attempts++;
    return malloc(size);
}

void probe_free(void *allocation)
{
    free(allocation);
}

static void test_growth(size_t hint, size_t initial_chunk)
{
    pep_arena_t *arena = nullptr;
    assert(pep_arena_init(&arena, hint) == PEP_ARENA_OK);
    size_t before = attempts;
    unsigned char *first = pep_arena_alloc(arena, initial_chunk, 1);
    assert(first != nullptr && attempts == before + 1);
    first[0] = 19;
    first[initial_chunk - 1] = 23;
    assert(pep_arena_alloc(arena, 1, 1) != nullptr && attempts == before + 2);
    assert(pep_arena_alloc(arena, 2 * initial_chunk - 1, 1) != nullptr);
    assert(attempts == before + 2);
    assert(pep_arena_alloc(arena, 1, 1) != nullptr && attempts == before + 3);
    assert(first[0] + first[initial_chunk - 1] == 42);
    pep_arena_free(&arena);
}

int main(void)
{
    test_growth(64, 64);
    test_growth(0, 4096);
}
