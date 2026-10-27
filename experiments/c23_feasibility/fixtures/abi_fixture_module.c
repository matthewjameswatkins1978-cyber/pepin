#include "abi_fixture_types.h"

#include <limits.h>
#include <stdlib.h>
#include <string.h>

_Static_assert(sizeof(int64_t) == 8, "fixture requires eight-bit bytes and 64-bit integers");
_Static_assert(offsetof(pep_fixture_point, x) == 0, "point x must be first");
_Static_assert(offsetof(pep_fixture_point, y) == sizeof(int64_t), "point y follows x");

static pep_status eval_tree(const pep_fixture_tree *tree, size_t depth,
                            size_t max_depth, int64_t *out) {
    if (tree == NULL || out == NULL) return PEP_ERR_RANGE;
    if (depth > max_depth || depth == SIZE_MAX) return PEP_ERR_DEPTH;
    switch (tree->tag) {
    case PEP_FIXTURE_LEAF:
        *out = tree->as.leaf;
        return PEP_OK;
    case PEP_FIXTURE_PAIR: {
        int64_t left = 0;
        int64_t right = 0;
        pep_status status = eval_tree(tree->as.pair.left, depth + 1, max_depth, &left);
        if (status != PEP_OK) return status;
        status = eval_tree(tree->as.pair.right, depth + 1, max_depth, &right);
        if (status != PEP_OK) return status;
        return pep_checked_add(left, right, out);
    }
    }
    return PEP_ERR_INVALID_VARIANT;
}

typedef struct {
    size_t allocations;
    size_t deallocations;
} fixture_allocator_state;

static void *fixture_allocate(void *context, size_t size) {
    fixture_allocator_state *state = context;
    void *memory = malloc(size);
    if (memory != NULL) state->allocations += 1;
    return memory;
}

static void fixture_deallocate(void *context, void *pointer) {
    fixture_allocator_state *state = context;
    if (pointer != NULL) state->deallocations += 1;
    free(pointer);
}

pep_status pep_abi_fixture_run(pep_fixture_report *out) {
    if (out == NULL) return PEP_ERR_RANGE;
    memset(out, 0, sizeof(*out));

    pep_fixture_point point = { 20, 22 };
    pep_status status = pep_checked_add(point.x, point.y, &out->point_sum);
    if (status != PEP_OK) return status;

    pep_fixture_tree left = { .tag = PEP_FIXTURE_LEAF, .as.leaf = 20 };
    pep_fixture_tree right = { .tag = PEP_FIXTURE_LEAF, .as.leaf = 22 };
    pep_fixture_tree root = {
        .tag = PEP_FIXTURE_PAIR,
        .as.pair = { .left = &left, .right = &right }
    };
    status = eval_tree(&root, 0, 8, &out->tree_sum);
    if (status != PEP_OK) return status;

    int64_t source[] = { 20, 22 };
    pep_i64_list list = { 0 };
    pep_i64_list extended = { 0 };
    status = pep_list_from_array(source, 2, &list);
    if (status == PEP_OK) status = pep_list_append(&list, 7, &extended);
    if (status == PEP_OK) status = pep_list_sum(&extended, &out->list_sum);
    pep_list_dispose(&list);
    pep_list_dispose(&extended);
    if (status != PEP_OK) return status;

    const unsigned char embedded_nul[] = { 'A', 0, 'B' };
    pep_str string = { NULL, 0 };
    status = pep_str_from_bytes(embedded_nul, sizeof(embedded_nul), &string);
    if (status != PEP_OK) return status;
    out->utf8_len = string.len;

    int64_t ignored = 0;
    out->overflow_status = pep_checked_add(INT64_MAX, 1, &ignored);
    if (out->overflow_status != PEP_ERR_OVERFLOW) return PEP_ERR_OVERFLOW;

    pep_fixture_tree invalid = { .tag = (pep_fixture_tree_tag)99 };
    out->invalid_tag_status = eval_tree(&invalid, 0, 8, &ignored);
    if (out->invalid_tag_status != PEP_ERR_INVALID_VARIANT) return PEP_ERR_INVALID_VARIANT;

    fixture_allocator_state owner_state = { 0 };
    fixture_allocator_state other_state = { 0 };
    pep_allocator owner = { fixture_allocate, fixture_deallocate, &owner_state };
    pep_allocator other = { fixture_allocate, fixture_deallocate, &other_state };
    pep_i64_list owned = { 0 };
    status = pep_list_from_array_with_allocator(source, 2, &owned, &owner);
    if (status != PEP_OK) return status;
    out->owner_mismatch_status = pep_list_dispose_with_allocator(&owned, &other);
    if (out->owner_mismatch_status != PEP_ERR_RANGE || owner_state.deallocations != 0 ||
        other_state.deallocations != 0) {
        pep_list_dispose(&owned);
        return PEP_ERR_RANGE;
    }
    out->owner_recovery_status = pep_list_dispose_with_allocator(&owned, &owner);
    if (out->owner_recovery_status != PEP_OK || owner_state.deallocations != 1) {
        return PEP_ERR_RANGE;
    }

    out->point_size = sizeof(pep_fixture_point);
    out->point_align = _Alignof(pep_fixture_point);
    out->point_y_offset = offsetof(pep_fixture_point, y);
    out->tree_size = sizeof(pep_fixture_tree);
    out->tree_align = _Alignof(pep_fixture_tree);
    out->tree_payload_offset = offsetof(pep_fixture_tree, as);
    return PEP_OK;
}
