/* Independent arena gate. Only the arena translation unit is compiled with
 * malloc/free renamed to these test-owned wrappers. All allocations are real
 * except the one deliberately failed; the production allocator is unchanged.
 */
#include "pep_arena.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static size_t malloc_calls;
static size_t live_allocations;
static size_t fail_at = SIZE_MAX;

void *lucy_test_malloc(size_t size)
{
    if (malloc_calls++ == fail_at) return nullptr;
    void *p = malloc(size);
    if (p != nullptr) live_allocations++;
    return p;
}

void lucy_test_free(void *p)
{
    if (p != nullptr) {
        assert(live_allocations > 0);
        live_allocations--;
    }
    free(p);
}

#define CHECK(condition) do { \
    if (!(condition)) { \
        fprintf(stderr, "arena assertion failed at line %d: %s\n", __LINE__, #condition); \
        return 1; \
    } \
} while (0)

static int failure_cases(void)
{
    pep_arena_t *arena = nullptr;
    CHECK(pep_arena_init(nullptr, 0) == PEP_ARENA_BADARG);
    CHECK(pep_arena_alloc(nullptr, 1, 1) == nullptr);
    CHECK(pep_arena_status(nullptr) == PEP_ARENA_BADARG);
    pep_arena_free(nullptr);
    pep_arena_free(&arena);

    fail_at = malloc_calls;
    CHECK(pep_arena_init(&arena, 16) == PEP_ARENA_ALLOC);
    CHECK(arena == nullptr && live_allocations == 0);
    fail_at = SIZE_MAX;

    CHECK(pep_arena_init(&arena, 16) == PEP_ARENA_OK);
    fail_at = malloc_calls;
    CHECK(pep_arena_alloc(arena, 16, 8) == nullptr);
    CHECK(pep_arena_status(arena) == PEP_ARENA_ALLOC);
    CHECK(live_allocations == 1); /* only the arena handle */
    fail_at = SIZE_MAX;
    CHECK(pep_arena_alloc(arena, 4, 1) == nullptr);
    CHECK(pep_arena_alloc(arena, 0, 0) == nullptr);
    CHECK(pep_arena_status(arena) == PEP_ARENA_ALLOC); /* first error sticky */
    pep_arena_free(&arena);
    CHECK(arena == nullptr && live_allocations == 0);

    CHECK(pep_arena_init(&arena, 16) == PEP_ARENA_OK);
    unsigned char *old = pep_arena_alloc(arena, 256, 64);
    CHECK(old != nullptr);
    for (size_t i = 0; i < 256; i++) old[i] = (unsigned char)i;
    fail_at = malloc_calls;
    CHECK(pep_arena_alloc(arena, 4096, 128) == nullptr);
    fail_at = SIZE_MAX;
    CHECK(pep_arena_status(arena) == PEP_ARENA_ALLOC);
    for (size_t i = 0; i < 256; i++) CHECK(old[i] == (unsigned char)i);
    CHECK(pep_arena_alloc(arena, 1, 1) == nullptr);
    pep_arena_free(&arena);
    CHECK(arena == nullptr && live_allocations == 0);
    return 0;
}

static int overflow_and_badarg_cases(void)
{
    for (size_t align = 1; align <= 8; align *= 8) {
        pep_arena_t *arena = nullptr;
        CHECK(pep_arena_init(&arena, 16) == PEP_ARENA_OK);
        size_t before = malloc_calls;
        CHECK(pep_arena_alloc(arena, SIZE_MAX, align) == nullptr);
        CHECK(pep_arena_status(arena) == PEP_ARENA_OVERFLOW);
        CHECK(malloc_calls == before); /* refuse before malloc */
        CHECK(pep_arena_alloc(arena, 1, 1) == nullptr);
        pep_arena_free(&arena);
        CHECK(arena == nullptr && live_allocations == 0);
    }
    pep_arena_t *a = nullptr, *b = nullptr;
    CHECK(pep_arena_init(&a, SIZE_MAX) == PEP_ARENA_OK);
    size_t before = malloc_calls;
    CHECK(pep_arena_alloc(a, 1, 1) == nullptr);
    CHECK(pep_arena_status(a) == PEP_ARENA_OVERFLOW && malloc_calls == before);
    pep_arena_free(&a);
    CHECK(pep_arena_init(&a, 0) == PEP_ARENA_OK);
    CHECK(pep_arena_init(&b, 0) == PEP_ARENA_OK);
    CHECK(pep_arena_alloc(a, 1, 3) == nullptr);
    CHECK(pep_arena_status(a) == PEP_ARENA_BADARG);
    CHECK(pep_arena_alloc(a, 1, 1) == nullptr);
    CHECK(pep_arena_alloc(b, 1, 1) != nullptr); /* separate arenas */
    CHECK(pep_arena_status(b) == PEP_ARENA_OK);
    CHECK(pep_arena_alloc(b, 0, 1) == nullptr);
    CHECK(pep_arena_status(b) == PEP_ARENA_BADARG);
    pep_arena_free(&a);
    pep_arena_free(&b);
    pep_arena_free(&b);
    CHECK(a == nullptr && b == nullptr && live_allocations == 0);
    return 0;
}

#define N 4096
static unsigned char *pointers[N];
static size_t sizes[N];
static uint32_t rng = 0xCAFE1234u;

static uint32_t next(void)
{
    rng ^= rng << 13;
    rng ^= rng >> 17;
    rng ^= rng << 5;
    return rng;
}

static unsigned char pattern(size_t i, size_t j)
{
    return (unsigned char)((i * 73 + j * 19) % 256);
}

static int stress_case(void)
{
    pep_arena_t *arena = nullptr;
    CHECK(pep_arena_init(&arena, 16) == PEP_ARENA_OK);
    for (size_t i = 0; i < N; i++) {
        size_t size = 1 + next() % 257;
        size_t align = (size_t)1 << (next() % 13);
        unsigned char *p = pep_arena_alloc(arena, size, align);
        CHECK(p != nullptr && (uintptr_t)p % align == 0);
        /* Integer addresses avoid relational comparisons between distinct
         * allocated C objects. Each checked interval must not overlap. */
        for (size_t j = 0; j < i; j++) {
            uintptr_t prev = (uintptr_t)pointers[j];
            uintptr_t cur = (uintptr_t)p;
            CHECK(cur + size <= prev || prev + sizes[j] <= cur);
        }
        pointers[i] = p;
        sizes[i] = size;
        for (size_t j = 0; j < size; j++) p[j] = pattern(i, j);
    }
    CHECK(live_allocations > 2); /* did grow beyond first chunk */
    for (size_t i = 0; i < N; i++) {
        for (size_t j = 0; j < sizes[i]; j++) CHECK(pointers[i][j] == pattern(i, j));
    }
    CHECK(pep_arena_status(arena) == PEP_ARENA_OK);
    pep_arena_free(&arena);
    CHECK(arena == nullptr && live_allocations == 0);
    printf("stress: %d nonoverlapping aligned allocations; all bytes retained\n", N);
    return 0;
}

int main(void)
{
    if (failure_cases() != 0) return 1;
    puts("allocation fault injection: handle, first chunk, later growth; sticky status and cleanup OK");
    if (overflow_and_badarg_cases() != 0) return 1;
    puts("overflow, invalid alignment/size, isolation and repeated free: OK");
    return stress_case();
}
