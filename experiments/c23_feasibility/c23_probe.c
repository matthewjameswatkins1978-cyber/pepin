#include "c23_runtime.h"

#include <inttypes.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>

static int failures = 0;

typedef struct {
    size_t remaining;
    size_t allocations;
    size_t deallocations;
} fail_allocator_state;

typedef struct {
    pep_point point;
    pep_i64_list values;
} nested_record;

static void *fail_allocate(void *context, size_t size) {
    fail_allocator_state *state = context;
    if (state->remaining == 0) return NULL;
    state->remaining -= 1;
    state->allocations += 1;
    return malloc(size);
}

static void fail_deallocate(void *context, void *pointer) {
    fail_allocator_state *state = context;
    state->deallocations += 1;
    free(pointer);
}

static void check_true(const char *name, bool condition) {
    if (condition) {
        printf("PASS|%s\n", name);
    } else {
        printf("FAIL|%s\n", name);
        failures += 1;
    }
}

static void check_status(const char *name, pep_status actual, pep_status expected) {
    if (actual == expected) {
        printf("PASS|%s|%s\n", name, pep_status_name(actual));
        printf("OBS|%s|%s\n", name, pep_status_name(actual));
    } else {
        printf("FAIL|%s|got=%s|expected=%s\n", name,
               pep_status_name(actual), pep_status_name(expected));
        failures += 1;
    }
}

static void check_i64(const char *name, int64_t actual, int64_t expected) {
    if (actual == expected) {
        printf("PASS|%s|%" PRId64 "\n", name, actual);
        printf("OBS|%s|%" PRId64 "\n", name, actual);
    } else {
        printf("FAIL|%s|got=%" PRId64 "|expected=%" PRId64 "\n", name, actual, expected);
        failures += 1;
    }
}

int main(void) {
    int64_t value = 0;
    check_true("int64_is_8_bytes", sizeof(int64_t) == 8);
    check_true("unsigned_char_is_8_bits", CHAR_BIT == 8);

    check_status("add_overflow", pep_checked_add(INT64_MAX, 1, &value), PEP_ERR_OVERFLOW);
    check_status("sub_overflow", pep_checked_sub(INT64_MIN, 1, &value), PEP_ERR_OVERFLOW);
    check_status("mul_overflow", pep_checked_mul(INT64_MIN, -1, &value), PEP_ERR_OVERFLOW);
    check_status("division_by_zero", pep_checked_div(1, 0, &value), PEP_ERR_DIVISION_BY_ZERO);
    check_status("division_min_by_negative_one", pep_checked_div(INT64_MIN, -1, &value), PEP_ERR_OVERFLOW);
    check_status("checked_add_value", pep_checked_add(20, 22, &value), PEP_OK);
    check_i64("checked_add_value_result", value, 42);
    check_status("checked_neg_min", pep_checked_neg(INT64_MIN, &value), PEP_ERR_OVERFLOW);

    static const unsigned char embedded_zero[] = { 'A', 0, 0xc2, 0xa2 };
    static const unsigned char invalid_utf8[] = { 0xc0, 0x80 };
    static const unsigned char truncated_utf8[] = { 0xe2, 0x82 };
    static const unsigned char surrogate_utf8[] = { 0xed, 0xa0, 0x80 };
    static const unsigned char bad_continuation_utf8[] = { 0xe2, 0x28, 0xa1 };
    static const unsigned char out_of_range_utf8[] = { 0xf4, 0x90, 0x80, 0x80 };
    pep_str text = { NULL, 0 };
    check_status("utf8_embedded_zero", pep_str_from_bytes(embedded_zero, sizeof(embedded_zero), &text), PEP_OK);
    check_true("utf8_embedded_zero_length", text.len == sizeof(embedded_zero));
    check_true("utf8_embedded_zero_identity", pep_str_equal(text, (pep_str){ embedded_zero, sizeof(embedded_zero) }));
    check_status("utf8_reject_overlong", pep_str_from_bytes(invalid_utf8, sizeof(invalid_utf8), &text), PEP_ERR_INVALID_UTF8);
    check_status("utf8_reject_truncated", pep_str_from_bytes(truncated_utf8, sizeof(truncated_utf8), &text), PEP_ERR_INVALID_UTF8);
    check_status("utf8_reject_surrogate", pep_str_from_bytes(surrogate_utf8, sizeof(surrogate_utf8), &text), PEP_ERR_INVALID_UTF8);
    check_status("utf8_reject_bad_continuation", pep_str_from_bytes(bad_continuation_utf8, sizeof(bad_continuation_utf8), &text), PEP_ERR_INVALID_UTF8);
    check_status("utf8_reject_out_of_range", pep_str_from_bytes(out_of_range_utf8, sizeof(out_of_range_utf8), &text), PEP_ERR_INVALID_UTF8);

    pep_point point = { 20, 22 };
    check_status("record_field_sum", pep_checked_add(point.x, point.y, &value), PEP_OK);
    check_i64("record_field_sum_result", value, 42);
    pep_unit unit = { 0 };
    check_true("unit_is_explicit_value", unit._unit == 0);

    pep_arena arena;
    check_status("arena_init", pep_arena_init(&arena, 64), PEP_OK);
    check_true("arena_empty_allocation_rejected", pep_arena_alloc(&arena, 0, 1) == NULL);
    check_true("arena_invalid_alignment_rejected", pep_arena_alloc(&arena, sizeof(int64_t), 3) == NULL);
    check_true("arena_oversized_allocation_rejected", pep_arena_alloc(&arena, SIZE_MAX, 1) == NULL);
    void *aligned = pep_arena_alloc(&arena, sizeof(int64_t), _Alignof(max_align_t));
    check_true("arena_alignment", aligned != NULL && ((uintptr_t)aligned % _Alignof(max_align_t)) == 0);
    pep_expr *left = pep_expr_number(&arena, 20);
    pep_expr *right = pep_expr_number(&arena, 22);
    pep_expr *expression = pep_expr_add(&arena, left, right);
    check_true("recursive_union_allocated", left != NULL && right != NULL && expression != NULL);
    check_status("recursive_union_match", pep_expr_eval(expression, 0, 32, &value), PEP_OK);
    check_i64("recursive_union_match_result", value, 42);
    pep_expr invalid = { (pep_expr_tag)99, { .number = 0 } };
    check_status("recursive_union_reject_invalid_tag", pep_expr_eval(&invalid, 0, 32, &value), PEP_ERR_INVALID_VARIANT);
    check_status("recursive_union_depth_limit", pep_expr_eval(expression, 0, 0, &value), PEP_ERR_DEPTH);
    check_status("recursive_union_depth_counter_overflow", pep_expr_eval(expression, SIZE_MAX, SIZE_MAX, &value), PEP_ERR_DEPTH);
    pep_arena_dispose(&arena);
    check_status("arena_reinit_after_dispose", pep_arena_init(&arena, 32), PEP_OK);
    check_true("arena_reuse_after_dispose", pep_arena_alloc(&arena, sizeof(int64_t), _Alignof(int64_t)) != NULL);
    pep_arena_dispose(&arena);

    fail_allocator_state allocation_state = { 1, 0, 0 };
    pep_allocator failing_allocator = { fail_allocate, fail_deallocate, &allocation_state };
    pep_allocator invalid_allocator = { NULL, NULL, NULL };
    pep_arena failing_arena;
    check_status("allocator_rejects_invalid_hooks", pep_arena_init_with_allocator(&failing_arena, 64, &invalid_allocator), PEP_ERR_RANGE);
    pep_arena_dispose(&failing_arena);
    check_status("allocator_injected_arena_init", pep_arena_init_with_allocator(&failing_arena, 64, &failing_allocator), PEP_OK);
    check_true("allocator_failure_does_not_publish_block", pep_arena_alloc(&failing_arena, sizeof(int64_t), _Alignof(int64_t)) == NULL &&
        failing_arena.first == NULL && pep_arena_reserved(&failing_arena) == 0 && allocation_state.deallocations == 1);
    allocation_state.remaining = 2;
    check_true("allocator_failure_recovers", pep_arena_alloc(&failing_arena, sizeof(int64_t), _Alignof(int64_t)) != NULL);
    pep_arena_dispose(&failing_arena);
    check_true("allocator_arena_disposes_all_blocks", allocation_state.deallocations == 3);

    const int64_t source_items[] = { 10, 12, 20 };
    pep_i64_list original = { 0 };
    pep_i64_list extended = { 0 };
    pep_i64_list empty = { 0 };
    check_status("empty_list", pep_list_from_array(NULL, 0, &empty), PEP_OK);
    check_true("empty_list_shape", empty.len == 0 && empty.items == NULL);
    pep_list_dispose(&empty);
    check_status("list_copy", pep_list_from_array(source_items, 3, &original), PEP_OK);
    check_status("list_append", pep_list_append(&original, 7, &extended), PEP_OK);
    check_status("list_rejects_aliasing_append", pep_list_append(&original, 7, &original), PEP_ERR_RANGE);
    check_status("list_sum_original", pep_list_sum(&original, &value), PEP_OK);
    check_i64("list_sum_original_result", value, 42);
    check_status("list_sum_extended", pep_list_sum(&extended, &value), PEP_OK);
    check_i64("list_sum_extended_result", value, 49);
    check_true("list_append_preserves_input", original.len == 3 && original.items[2] == 20);
    nested_record record = { { 20, 22 }, extended };
    check_status("nested_record_list_sum", pep_list_sum(&record.values, &value), PEP_OK);
    check_i64("nested_record_list_sum_result", value, 49);
    check_status("list_get_range", pep_list_get(&original, 3, &value), PEP_ERR_RANGE);
    const int64_t allocation_guard = 0;
    pep_i64_list rejected = { 0 };
    check_status("list_allocation_overflow", pep_list_from_array(&allocation_guard, SIZE_MAX, &rejected), PEP_ERR_ALLOCATION);
    allocation_state.remaining = 0;
    pep_i64_list failed_list = { 0 };
    check_status("list_allocator_failure", pep_list_from_array_with_allocator(source_items, 3, &failed_list, &failing_allocator), PEP_ERR_ALLOCATION);
    check_true("list_allocator_failure_preserves_output", failed_list.items == NULL && failed_list.len == 0);
    allocation_state.remaining = 1;
    check_status("list_allocator_recovery", pep_list_from_array_with_allocator(source_items, 3, &failed_list, &failing_allocator), PEP_OK);
    pep_list_dispose(&failed_list);
    check_true("list_allocator_disposes_recovered_buffer", allocation_state.deallocations == 4);
    pep_list_dispose(&original);
    pep_list_dispose(&extended);

    check_status("recursive_factorial", pep_factorial(5, 0, 64, &value), PEP_OK);
    check_i64("recursive_factorial_result", value, 120);
    check_status("recursive_factorial_overflow", pep_factorial(21, 0, 64, &value), PEP_ERR_OVERFLOW);
    check_status("recursive_factorial_depth_counter_overflow", pep_factorial(1, SIZE_MAX, SIZE_MAX, &value), PEP_ERR_DEPTH);
    check_status("while_for_sum", pep_sum_to(101, &value), PEP_OK);
    check_i64("while_for_sum_result", value, 5050);

    printf("SUMMARY|failures=%d\n", failures);
    return failures == 0 ? 0 : 1;
}
