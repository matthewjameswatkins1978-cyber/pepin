#include "c23_runtime.h"

#include <inttypes.h>
#include <limits.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

struct pep_arena_block {
    unsigned char *data;
    size_t capacity;
    size_t used;
    struct pep_arena_block *next;
};

static bool size_add_overflow(size_t left, size_t right, size_t *out) {
    if (right > SIZE_MAX - left) {
        return true;
    }
    *out = left + right;
    return false;
}

static bool size_mul_overflow(size_t left, size_t right, size_t *out) {
    if (left != 0 && right > SIZE_MAX / left) {
        return true;
    }
    *out = left * right;
    return false;
}

static void *pep_default_allocate(void *context, size_t size) {
    (void)context;
    return malloc(size);
}

static void pep_default_deallocate(void *context, void *pointer) {
    (void)context;
    free(pointer);
}

pep_allocator pep_allocator_default(void) {
    return (pep_allocator){ pep_default_allocate, pep_default_deallocate, NULL };
}

static bool pep_allocator_valid(const pep_allocator *allocator) {
    return allocator != NULL && allocator->allocate != NULL && allocator->deallocate != NULL;
}

const char *pep_status_name(pep_status status) {
    switch (status) {
    case PEP_OK: return "ok";
    case PEP_ERR_OVERFLOW: return "overflow";
    case PEP_ERR_DIVISION_BY_ZERO: return "division_by_zero";
    case PEP_ERR_INVALID_UTF8: return "invalid_utf8";
    case PEP_ERR_RANGE: return "range";
    case PEP_ERR_ALLOCATION: return "allocation";
    case PEP_ERR_INVALID_VARIANT: return "invalid_variant";
    case PEP_ERR_DEPTH: return "depth";
    }
    return "unknown_status";
}

static bool pep_utf8_valid(const unsigned char *data, size_t len) {
    size_t index = 0;
    while (index < len) {
        unsigned char first = data[index];
        size_t width = 0;
        uint32_t codepoint = 0;
        uint32_t minimum = 0;

        if (first <= 0x7fu) {
            index += 1;
            continue;
        }
        if (first >= 0xc2u && first <= 0xdfu) {
            width = 2;
            codepoint = (uint32_t)(first & 0x1fu);
            minimum = 0x80u;
        } else if (first >= 0xe0u && first <= 0xefu) {
            width = 3;
            codepoint = (uint32_t)(first & 0x0fu);
            minimum = 0x800u;
        } else if (first >= 0xf0u && first <= 0xf4u) {
            width = 4;
            codepoint = (uint32_t)(first & 0x07u);
            minimum = 0x10000u;
        } else {
            return false;
        }
        if (width > len - index) {
            return false;
        }
        for (size_t offset = 1; offset < width; ++offset) {
            unsigned char next = data[index + offset];
            if (next < 0x80u || next > 0xbfu) {
                return false;
            }
            codepoint = (codepoint * 64u) + (uint32_t)(next & 0x3fu);
        }
        if (codepoint < minimum || codepoint > 0x10ffffu ||
            (codepoint >= 0xd800u && codepoint <= 0xdfffu)) {
            return false;
        }
        index += width;
    }
    return true;
}

pep_status pep_str_from_bytes(const unsigned char *data, size_t len, pep_str *out) {
    if (len != 0 && data == NULL) {
        return PEP_ERR_RANGE;
    }
    if (!pep_utf8_valid(data, len)) {
        return PEP_ERR_INVALID_UTF8;
    }
    out->data = data;
    out->len = len;
    return PEP_OK;
}

bool pep_str_equal(pep_str left, pep_str right) {
    return left.len == right.len &&
        (left.len == 0 || memcmp(left.data, right.data, left.len) == 0);
}

pep_status pep_checked_add(int64_t left, int64_t right, int64_t *out) {
    if ((right > 0 && left > INT64_MAX - right) ||
        (right < 0 && left < INT64_MIN - right)) {
        return PEP_ERR_OVERFLOW;
    }
    *out = left + right;
    return PEP_OK;
}

pep_status pep_checked_sub(int64_t left, int64_t right, int64_t *out) {
    if ((right > 0 && left < INT64_MIN + right) ||
        (right < 0 && left > INT64_MAX + right)) {
        return PEP_ERR_OVERFLOW;
    }
    *out = left - right;
    return PEP_OK;
}

pep_status pep_checked_mul(int64_t left, int64_t right, int64_t *out) {
    if (left == 0 || right == 0) {
        *out = 0;
        return PEP_OK;
    }
    if ((left == INT64_MIN && right == -1) ||
        (right == INT64_MIN && left == -1)) {
        return PEP_ERR_OVERFLOW;
    }
    if (left > 0) {
        if (right > 0 && left > INT64_MAX / right) return PEP_ERR_OVERFLOW;
        if (right < 0 && right < INT64_MIN / left) return PEP_ERR_OVERFLOW;
    } else if (right > 0) {
        if (left < INT64_MIN / right) return PEP_ERR_OVERFLOW;
    } else if (left < INT64_MAX / right) {
        return PEP_ERR_OVERFLOW;
    }
    *out = left * right;
    return PEP_OK;
}

pep_status pep_checked_div(int64_t left, int64_t right, int64_t *out) {
    if (right == 0) {
        return PEP_ERR_DIVISION_BY_ZERO;
    }
    if (left == INT64_MIN && right == -1) {
        return PEP_ERR_OVERFLOW;
    }
    *out = left / right;
    return PEP_OK;
}

pep_status pep_checked_neg(int64_t value, int64_t *out) {
    if (value == INT64_MIN) {
        return PEP_ERR_OVERFLOW;
    }
    *out = -value;
    return PEP_OK;
}

pep_status pep_arena_init_with_allocator(pep_arena *arena, size_t initial_capacity,
                                          const pep_allocator *allocator) {
    if (arena == NULL) return PEP_ERR_RANGE;
    arena->first = NULL;
    arena->next_capacity = 0;
    arena->reserved_bytes = 0;
    arena->allocator = pep_allocator_default();
    if (allocator == NULL) {
        arena->allocator = pep_allocator_default();
    } else if (!pep_allocator_valid(allocator)) {
        return PEP_ERR_RANGE;
    } else {
        arena->allocator = *allocator;
    }
    arena->first = NULL;
    arena->next_capacity = initial_capacity == 0 ? 256 : initial_capacity;
    arena->reserved_bytes = 0;
    return PEP_OK;
}

pep_status pep_arena_init(pep_arena *arena, size_t initial_capacity) {
    return pep_arena_init_with_allocator(arena, initial_capacity, NULL);
}

void pep_arena_dispose(pep_arena *arena) {
    if (arena == NULL) return;
    pep_allocator selected = pep_allocator_valid(&arena->allocator) ?
        arena->allocator : pep_allocator_default();
    pep_arena_block *block = arena->first;
    while (block != NULL) {
        pep_arena_block *next = block->next;
        selected.deallocate(selected.context, block->data);
        selected.deallocate(selected.context, block);
        block = next;
    }
    arena->first = NULL;
    arena->next_capacity = 0;
    arena->reserved_bytes = 0;
    arena->allocator = pep_allocator_default();
}

void *pep_arena_alloc(pep_arena *arena, size_t size, size_t alignment) {
    if (arena == NULL || !pep_allocator_valid(&arena->allocator) || size == 0 ||
        size > PEP_MAX_ALLOCATION_SIZE ||
        alignment == 0 || alignment > _Alignof(max_align_t) ||
        (alignment & (alignment - 1)) != 0) {
        return NULL;
    }
    pep_arena_block *block = arena->first;
    size_t padding = 0;
    if (block != NULL) {
        size_t remainder = block->used & (alignment - 1);
        padding = remainder == 0 ? 0 : alignment - remainder;
        size_t needed = 0;
        if (!size_add_overflow(padding, size, &needed) && needed <= block->capacity - block->used) {
            void *result = block->data + block->used + padding;
            block->used += needed;
            return result;
        }
    }

    size_t capacity = arena->next_capacity;
    size_t needed = 0;
    if (size_add_overflow(size, alignment - 1, &needed)) {
        return NULL;
    }
    if (capacity < needed) {
        capacity = needed;
    }
    pep_arena_block *new_block = arena->allocator.allocate(arena->allocator.context, sizeof(*new_block));
    if (new_block == NULL) {
        return NULL;
    }
    new_block->data = arena->allocator.allocate(arena->allocator.context, capacity);
    if (new_block->data == NULL) {
        arena->allocator.deallocate(arena->allocator.context, new_block);
        return NULL;
    }
    if (capacity > SIZE_MAX - arena->reserved_bytes) {
        arena->allocator.deallocate(arena->allocator.context, new_block->data);
        arena->allocator.deallocate(arena->allocator.context, new_block);
        return NULL;
    }
    new_block->capacity = capacity;
    new_block->used = 0;
    new_block->next = arena->first;
    arena->first = new_block;
    arena->reserved_bytes += capacity;
    arena->next_capacity = capacity > SIZE_MAX / 2 ? capacity : capacity * 2;
    return pep_arena_alloc(arena, size, alignment);
}

size_t pep_arena_reserved(const pep_arena *arena) {
    return arena == NULL ? 0 : arena->reserved_bytes;
}

pep_expr *pep_expr_number(pep_arena *arena, int64_t value) {
    pep_expr *expression = pep_arena_alloc(arena, sizeof(*expression), _Alignof(pep_expr));
    if (expression == NULL) return NULL;
    expression->tag = PEP_EXPR_NUMBER;
    expression->as.number = value;
    return expression;
}

pep_expr *pep_expr_add(pep_arena *arena, const pep_expr *left, const pep_expr *right) {
    pep_expr *expression = pep_arena_alloc(arena, sizeof(*expression), _Alignof(pep_expr));
    if (expression == NULL) return NULL;
    expression->tag = PEP_EXPR_ADD;
    expression->as.add.left = left;
    expression->as.add.right = right;
    return expression;
}

pep_status pep_expr_eval(const pep_expr *expression, size_t depth, size_t max_depth, int64_t *out) {
    if (expression == NULL) return PEP_ERR_RANGE;
    if (depth > max_depth || depth == SIZE_MAX) return PEP_ERR_DEPTH;
    switch (expression->tag) {
    case PEP_EXPR_NUMBER:
        *out = expression->as.number;
        return PEP_OK;
    case PEP_EXPR_ADD: {
        int64_t left = 0;
        int64_t right = 0;
        pep_status status = pep_expr_eval(expression->as.add.left, depth + 1, max_depth, &left);
        if (status != PEP_OK) return status;
        status = pep_expr_eval(expression->as.add.right, depth + 1, max_depth, &right);
        if (status != PEP_OK) return status;
        return pep_checked_add(left, right, out);
    }
    }
    return PEP_ERR_INVALID_VARIANT;
}

pep_status pep_list_from_array_with_allocator(const int64_t *items, size_t len,
                                               pep_i64_list *out,
                                               const pep_allocator *allocator) {
    pep_allocator selected = pep_allocator_default();
    if (out == NULL) return PEP_ERR_RANGE;
    if (allocator != NULL) {
        if (!pep_allocator_valid(allocator)) return PEP_ERR_RANGE;
        selected = *allocator;
    }
    size_t bytes = 0;
    if (len != 0 && items == NULL) return PEP_ERR_RANGE;
    if (size_mul_overflow(len, sizeof(*items), &bytes) || bytes > PEP_MAX_ALLOCATION_SIZE) return PEP_ERR_ALLOCATION;
    int64_t *new_items = bytes == 0 ? NULL : selected.allocate(selected.context, bytes);
    if (bytes != 0 && new_items == NULL) return PEP_ERR_ALLOCATION;
    if (bytes != 0) memcpy(new_items, items, bytes);
    out->items = new_items;
    out->len = len;
    out->allocator = selected;
    return PEP_OK;
}

pep_status pep_list_from_array(const int64_t *items, size_t len, pep_i64_list *out) {
    return pep_list_from_array_with_allocator(items, len, out, NULL);
}

pep_status pep_list_append_with_allocator(const pep_i64_list *input, int64_t value,
                                          pep_i64_list *out,
                                          const pep_allocator *allocator) {
    if (input == NULL || (input->len != 0 && input->items == NULL)) return PEP_ERR_RANGE;
    if (out == NULL || out == input) return PEP_ERR_RANGE;
    pep_allocator selected = pep_allocator_default();
    if (allocator != NULL) {
        if (!pep_allocator_valid(allocator)) return PEP_ERR_RANGE;
        selected = *allocator;
    }
    if (input->len == SIZE_MAX) return PEP_ERR_ALLOCATION;
    size_t new_length = input->len + 1;
    size_t bytes = 0;
    if (new_length > SIZE_MAX / sizeof(*input->items)) return PEP_ERR_ALLOCATION;
    bytes = new_length * sizeof(*input->items);
    if (bytes > PEP_MAX_ALLOCATION_SIZE) return PEP_ERR_ALLOCATION;
    int64_t *new_items = selected.allocate(selected.context, bytes);
    if (new_items == NULL) return PEP_ERR_ALLOCATION;
    if (input->len != 0) memcpy(new_items, input->items, input->len * sizeof(*input->items));
    new_items[input->len] = value;
    out->items = new_items;
    out->len = new_length;
    out->allocator = selected;
    return PEP_OK;
}

pep_status pep_list_append(const pep_i64_list *input, int64_t value, pep_i64_list *out) {
    return pep_list_append_with_allocator(input, value, out, NULL);
}

pep_status pep_list_get(const pep_i64_list *list, size_t index, int64_t *out) {
    if (list == NULL || index >= list->len || list->items == NULL) return PEP_ERR_RANGE;
    *out = list->items[index];
    return PEP_OK;
}

pep_status pep_list_sum(const pep_i64_list *list, int64_t *out) {
    if (list == NULL || (list->len != 0 && list->items == NULL)) return PEP_ERR_RANGE;
    int64_t total = 0;
    for (size_t index = 0; index < list->len; ++index) {
        pep_status status = pep_checked_add(total, list->items[index], &total);
        if (status != PEP_OK) return status;
    }
    *out = total;
    return PEP_OK;
}

void pep_list_dispose(pep_i64_list *list) {
    pep_list_dispose_with_allocator(list, NULL);
}

void pep_list_dispose_with_allocator(pep_i64_list *list, const pep_allocator *allocator) {
    if (list == NULL) return;
    pep_allocator selected = list->allocator;
    if (allocator != NULL && pep_allocator_valid(allocator)) selected = *allocator;
    if (list->items != NULL && pep_allocator_valid(&selected)) {
        selected.deallocate(selected.context, list->items);
    }
    list->items = NULL;
    list->len = 0;
    list->allocator = pep_allocator_default();
}

pep_status pep_factorial(int64_t value, size_t depth, size_t max_depth, int64_t *out) {
    if (value < 0) return PEP_ERR_RANGE;
    if (depth > max_depth || depth == SIZE_MAX) return PEP_ERR_DEPTH;
    if (value == 0) {
        *out = 1;
        return PEP_OK;
    }
    int64_t previous = 0;
    pep_status status = pep_factorial(value - 1, depth + 1, max_depth, &previous);
    if (status != PEP_OK) return status;
    return pep_checked_mul(value, previous, out);
}

pep_status pep_sum_to(int64_t limit, int64_t *out) {
    if (limit < 0) return PEP_ERR_RANGE;
    int64_t total = 0;
    for (int64_t value = 0; value < limit; ++value) {
        pep_status status = pep_checked_add(total, value, &total);
        if (status != PEP_OK) return status;
    }
    *out = total;
    return PEP_OK;
}
