#include "c23_runtime.h"

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifdef _WIN32
#include <windows.h>
#endif

#define PEP_BENCHMARK_MAX_SIZE (UINTMAX_C(1024) * UINTMAX_C(1024))

static int fail(const char *message) {
    fprintf(stderr, "BENCH_ERROR|%s\n", message);
    return 2;
}

static bool parse_size(const char *text, size_t *out) {
    char *end = NULL;
    uintmax_t value = strtoumax(text, &end, 10);
    if (text[0] == '\0' || end == text || *end != '\0' || value == 0 || value > SIZE_MAX) return false;
    *out = (size_t)value;
    return true;
}

static bool monotonic_ns(uintmax_t *out) {
#ifdef _WIN32
    LARGE_INTEGER counter = { 0 };
    LARGE_INTEGER frequency = { 0 };
    if (!QueryPerformanceCounter(&counter) || !QueryPerformanceFrequency(&frequency) ||
        counter.QuadPart < 0 || frequency.QuadPart <= 0) {
        return false;
    }
    uintmax_t ticks = (uintmax_t)counter.QuadPart;
    uintmax_t hz = (uintmax_t)frequency.QuadPart;
    uintmax_t seconds = ticks / hz;
    uintmax_t remainder = ticks % hz;
    if (seconds > UINTMAX_MAX / UINTMAX_C(1000000000) ||
        remainder > UINTMAX_MAX / UINTMAX_C(1000000000)) {
        return false;
    }
    uintmax_t result = seconds * UINTMAX_C(1000000000);
    uintmax_t fraction = (remainder * UINTMAX_C(1000000000)) / hz;
    if (fraction > UINTMAX_MAX - result) return false;
    *out = result + fraction;
    return true;
#else
    struct timespec stamp = { 0 };
    if (timespec_get(&stamp, TIME_UTC) != TIME_UTC || stamp.tv_sec < 0) return false;
    uintmax_t seconds = (uintmax_t)stamp.tv_sec;
    if (seconds > UINTMAX_MAX / UINTMAX_C(1000000000)) return false;
    uintmax_t result = seconds * UINTMAX_C(1000000000);
    if ((uintmax_t)stamp.tv_nsec > UINTMAX_MAX - result) return false;
    *out = result + (uintmax_t)stamp.tv_nsec;
    return true;
#endif
}

static bool checked_operations(size_t size, size_t iterations, size_t *out) {
    if (iterations != 0 && size > SIZE_MAX / iterations) return false;
    *out = size * iterations;
    return true;
}

static int run_arithmetic(size_t size, size_t iterations, uintmax_t *checksum, size_t *bytes, size_t *reserved) {
    int64_t total = 0;
    for (size_t iteration = 0; iteration < iterations; ++iteration) {
        for (size_t index = 0; index < size; ++index) {
            int64_t next = 0;
            pep_status status = pep_checked_add(total, (int64_t)(index % 97), &next);
            if (status != PEP_OK) return fail("arithmetic status");
            total = next;
        }
    }
    *checksum = (uintmax_t)total;
    *bytes = 0;
    *reserved = 0;
    return 0;
}

static int run_records(size_t size, size_t iterations, uintmax_t *checksum, size_t *bytes, size_t *reserved) {
    pep_point point = { 20, 22 };
    int64_t total = 0;
    for (size_t iteration = 0; iteration < iterations; ++iteration) {
        for (size_t index = 0; index < size; ++index) {
            int64_t next = 0;
            pep_status status = pep_checked_add(point.x, point.y, &next);
            if (status != PEP_OK) return fail("record status");
            status = pep_checked_add(total, next, &next);
            if (status != PEP_OK) return fail("record total overflow");
            total = next;
        }
    }
    *checksum = (uintmax_t)total;
    *bytes = 0;
    *reserved = 0;
    return 0;
}

static int run_union(size_t size, size_t iterations, uintmax_t *checksum, size_t *bytes, size_t *reserved) {
    int64_t total = 0;
    size_t peak_reserved = 0;
    for (size_t iteration = 0; iteration < iterations; ++iteration) {
        pep_arena arena;
        if (pep_arena_init(&arena, 64) != PEP_OK) return fail("union arena init");
        pep_expr *expression = pep_expr_number(&arena, 0);
        if (expression == NULL) { pep_arena_dispose(&arena); return fail("union allocation"); }
        for (size_t index = 0; index < size; ++index) {
            pep_expr *right = pep_expr_number(&arena, 1);
            if (right == NULL) { pep_arena_dispose(&arena); return fail("union allocation"); }
            expression = pep_expr_add(&arena, expression, right);
            if (expression == NULL) { pep_arena_dispose(&arena); return fail("union allocation"); }
        }
        int64_t value = 0;
        pep_status status = pep_expr_eval(expression, 0, size + 1, &value);
        if (status != PEP_OK) { pep_arena_dispose(&arena); return fail("union evaluation"); }
        int64_t updated = 0;
        if (pep_checked_add(total, value, &updated) != PEP_OK) {
            pep_arena_dispose(&arena);
            return fail("union total overflow");
        }
        total = updated;
        if (pep_arena_reserved(&arena) > peak_reserved) peak_reserved = pep_arena_reserved(&arena);
        pep_arena_dispose(&arena);
    }
    *checksum = (uintmax_t)total;
    *bytes = size * sizeof(pep_expr);
    *reserved = peak_reserved;
    return 0;
}

static int run_arena(size_t size, size_t iterations, uintmax_t *checksum, size_t *bytes, size_t *reserved) {
    uintmax_t total = 0;
    size_t peak_reserved = 0;
    for (size_t iteration = 0; iteration < iterations; ++iteration) {
        pep_arena arena;
        if (pep_arena_init(&arena, 64) != PEP_OK) return fail("arena init");
        for (size_t index = 0; index < size; ++index) {
            int64_t *slot = pep_arena_alloc(&arena, sizeof(*slot), _Alignof(int64_t));
            if (slot == NULL) { pep_arena_dispose(&arena); return fail("arena allocation"); }
            *slot = (int64_t)index;
            total += (uintmax_t)*slot;
        }
        if (pep_arena_reserved(&arena) > peak_reserved) peak_reserved = pep_arena_reserved(&arena);
        pep_arena_dispose(&arena);
    }
    *checksum = total;
    *bytes = size * sizeof(int64_t);
    *reserved = peak_reserved;
    return 0;
}

static int run_lists(size_t size, size_t iterations, uintmax_t *checksum, size_t *bytes, size_t *reserved) {
    if (size > (SIZE_MAX - 1) / 2 || size > SIZE_MAX / sizeof(int64_t)) return fail("list size overflow");
    int64_t *source = malloc(size * sizeof(*source));
    if (source == NULL) return fail("list source allocation");
    for (size_t index = 0; index < size; ++index) source[index] = (int64_t)(index % 97);
    uintmax_t total = 0;
    for (size_t iteration = 0; iteration < iterations; ++iteration) {
        pep_i64_list list = { 0 };
        pep_i64_list appended = { 0 };
        int64_t sum = 0;
        if (pep_list_from_array(source, size, &list) != PEP_OK ||
            pep_list_append(&list, 7, &appended) != PEP_OK ||
            pep_list_sum(&appended, &sum) != PEP_OK) {
            pep_list_dispose(&list);
            pep_list_dispose(&appended);
            free(source);
            return fail("list operation");
        }
        total += (uintmax_t)sum;
        pep_list_dispose(&list);
        pep_list_dispose(&appended);
    }
    free(source);
    *checksum = total;
    *bytes = (size + size + 1) * sizeof(int64_t);
    *reserved = 0;
    return 0;
}

static int run_recursive(size_t size, size_t iterations, uintmax_t *checksum, size_t *bytes, size_t *reserved) {
    pep_arena arena;
    if (pep_arena_init(&arena, 64) != PEP_OK) return fail("recursive arena init");
    pep_expr *expression = pep_expr_number(&arena, 0);
    if (expression == NULL) { pep_arena_dispose(&arena); return fail("recursive allocation"); }
    for (size_t index = 0; index < size; ++index) {
        pep_expr *right = pep_expr_number(&arena, 1);
        if (right == NULL) { pep_arena_dispose(&arena); return fail("recursive allocation"); }
        expression = pep_expr_add(&arena, expression, right);
        if (expression == NULL) { pep_arena_dispose(&arena); return fail("recursive allocation"); }
    }
    int64_t total = 0;
    for (size_t iteration = 0; iteration < iterations; ++iteration) {
        int64_t value = 0;
        if (pep_expr_eval(expression, 0, size + 1, &value) != PEP_OK) {
            pep_arena_dispose(&arena);
            return fail("recursive evaluation");
        }
        int64_t updated = 0;
        if (pep_checked_add(total, value, &updated) != PEP_OK) {
            pep_arena_dispose(&arena);
            return fail("recursive total overflow");
        }
        total = updated;
    }
    *checksum = (uintmax_t)total;
    *bytes = (size + size + 1) * sizeof(pep_expr);
    *reserved = pep_arena_reserved(&arena);
    pep_arena_dispose(&arena);
    return 0;
}

static int run_utf8(size_t size, size_t iterations, uintmax_t *checksum, size_t *bytes, size_t *reserved) {
    unsigned char *data = malloc(size);
    if (data == NULL) return fail("UTF-8 source allocation");
    memset(data, 'a', size);
    uintmax_t total = 0;
    for (size_t iteration = 0; iteration < iterations; ++iteration) {
        pep_str value = { NULL, 0 };
        if (pep_str_from_bytes(data, size, &value) != PEP_OK) {
            free(data);
            return fail("UTF-8 validation");
        }
        total += value.len;
    }
    free(data);
    *checksum = total;
    *bytes = size;
    *reserved = 0;
    return 0;
}

int main(int argc, char **argv) {
    if (argc != 4) return fail("usage: <case> <size> <iterations>");
    const char *name = argv[1];
    size_t size = 0;
    size_t iterations = 0;
    if (!parse_size(argv[2], &size) || !parse_size(argv[3], &iterations)) return fail("invalid size or iterations");
    if (size > PEP_BENCHMARK_MAX_SIZE || size == SIZE_MAX) return fail("benchmark size exceeds bounded corpus limit");
    size_t operations = 0;
    if (!checked_operations(size, iterations, &operations)) return fail("operation count overflow");

    uintmax_t checksum = 0;
    size_t bytes = 0;
    size_t reserved = 0;
    uintmax_t start = 0;
    if (!monotonic_ns(&start)) return fail("clock unavailable");
    int status = 0;
    if (strcmp(name, "arithmetic") == 0) status = run_arithmetic(size, iterations, &checksum, &bytes, &reserved);
    else if (strcmp(name, "record") == 0) status = run_records(size, iterations, &checksum, &bytes, &reserved);
    else if (strcmp(name, "union") == 0) status = run_union(size, iterations, &checksum, &bytes, &reserved);
    else if (strcmp(name, "arena") == 0) status = run_arena(size, iterations, &checksum, &bytes, &reserved);
    else if (strcmp(name, "list") == 0) status = run_lists(size, iterations, &checksum, &bytes, &reserved);
    else if (strcmp(name, "recursive") == 0) status = run_recursive(size, iterations, &checksum, &bytes, &reserved);
    else if (strcmp(name, "utf8") == 0) status = run_utf8(size, iterations, &checksum, &bytes, &reserved);
    else return fail("unknown benchmark case");
    if (status != 0) return status;
    uintmax_t finish = 0;
    if (!monotonic_ns(&finish) || finish < start) return fail("clock moved backwards");
    uintmax_t elapsed = finish - start;
#ifdef _WIN32
    const char *clock_name = "qpc";
#else
    const char *clock_name = "timespec_get_utc";
#endif
    printf("BENCH|case=%s|size=%zu|iterations=%zu|operations=%zu|checksum=%" PRIuMAX "|bytes=%zu|reserved=%zu|elapsed_ns=%" PRIuMAX "|clock=%s\n",
           name, size, iterations, operations, checksum, bytes, reserved, elapsed, clock_name);
    return 0;
}
