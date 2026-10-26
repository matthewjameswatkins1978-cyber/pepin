#ifndef PEP_C23_FEASIBILITY_RUNTIME_H
#define PEP_C23_FEASIBILITY_RUNTIME_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define PEP_MAX_ALLOCATION_SIZE (SIZE_MAX / 2)

typedef enum {
    PEP_OK = 0,
    PEP_ERR_OVERFLOW,
    PEP_ERR_DIVISION_BY_ZERO,
    PEP_ERR_INVALID_UTF8,
    PEP_ERR_RANGE,
    PEP_ERR_ALLOCATION,
    PEP_ERR_INVALID_VARIANT,
    PEP_ERR_DEPTH
} pep_status;

const char *pep_status_name(pep_status status);

typedef struct {
    const unsigned char *data;
    size_t len;
} pep_str;

pep_status pep_str_from_bytes(const unsigned char *data, size_t len, pep_str *out);
bool pep_str_equal(pep_str left, pep_str right);

typedef struct {
    unsigned char _unit;
} pep_unit;

typedef struct {
    int64_t x;
    int64_t y;
} pep_point;

pep_status pep_checked_add(int64_t left, int64_t right, int64_t *out);
pep_status pep_checked_sub(int64_t left, int64_t right, int64_t *out);
pep_status pep_checked_mul(int64_t left, int64_t right, int64_t *out);
pep_status pep_checked_div(int64_t left, int64_t right, int64_t *out);
pep_status pep_checked_neg(int64_t value, int64_t *out);

typedef void *(*pep_allocate_fn)(void *context, size_t size);
typedef void (*pep_deallocate_fn)(void *context, void *pointer);
typedef struct {
    pep_allocate_fn allocate;
    pep_deallocate_fn deallocate;
    void *context;
} pep_allocator;

pep_allocator pep_allocator_default(void);

typedef struct pep_arena_block pep_arena_block;
typedef struct {
    pep_arena_block *first;
    size_t next_capacity;
    size_t reserved_bytes;
    pep_allocator allocator;
} pep_arena;

pep_status pep_arena_init(pep_arena *arena, size_t initial_capacity);
pep_status pep_arena_init_with_allocator(pep_arena *arena, size_t initial_capacity,
                                          const pep_allocator *allocator);
void pep_arena_dispose(pep_arena *arena);
void *pep_arena_alloc(pep_arena *arena, size_t size, size_t alignment);
size_t pep_arena_reserved(const pep_arena *arena);

typedef enum {
    PEP_EXPR_NUMBER = 0,
    PEP_EXPR_ADD = 1
} pep_expr_tag;

typedef struct pep_expr pep_expr;
struct pep_expr {
    pep_expr_tag tag;
    union {
        int64_t number;
        struct {
            const pep_expr *left;
            const pep_expr *right;
        } add;
    } as;
};

pep_expr *pep_expr_number(pep_arena *arena, int64_t value);
pep_expr *pep_expr_add(pep_arena *arena, const pep_expr *left, const pep_expr *right);
pep_status pep_expr_eval(const pep_expr *expression, size_t depth, size_t max_depth, int64_t *out);

typedef struct {
    size_t len;
    int64_t *items;
    pep_allocator allocator;
} pep_i64_list;

pep_status pep_list_from_array(const int64_t *items, size_t len, pep_i64_list *out);
pep_status pep_list_from_array_with_allocator(const int64_t *items, size_t len,
                                               pep_i64_list *out,
                                               const pep_allocator *allocator);
pep_status pep_list_append(const pep_i64_list *input, int64_t value, pep_i64_list *out);
pep_status pep_list_append_with_allocator(const pep_i64_list *input, int64_t value,
                                          pep_i64_list *out,
                                          const pep_allocator *allocator);
pep_status pep_list_get(const pep_i64_list *list, size_t index, int64_t *out);
pep_status pep_list_sum(const pep_i64_list *list, int64_t *out);
void pep_list_dispose(pep_i64_list *list);
pep_status pep_list_dispose_with_allocator(pep_i64_list *list, const pep_allocator *allocator);

pep_status pep_factorial(int64_t value, size_t depth, size_t max_depth, int64_t *out);
pep_status pep_sum_to(int64_t limit, int64_t *out);

#endif
