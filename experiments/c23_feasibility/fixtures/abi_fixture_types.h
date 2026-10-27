#ifndef PEP_C23_ABI_FIXTURE_TYPES_H
#define PEP_C23_ABI_FIXTURE_TYPES_H

#include "../c23_runtime.h"

#include <stddef.h>
#include <stdint.h>

typedef struct {
    int64_t x;
    int64_t y;
} pep_fixture_point;

typedef enum {
    PEP_FIXTURE_LEAF = 0,
    PEP_FIXTURE_PAIR = 1
} pep_fixture_tree_tag;

typedef struct pep_fixture_tree pep_fixture_tree;
struct pep_fixture_tree {
    pep_fixture_tree_tag tag;
    union {
        int64_t leaf;
        struct {
            const pep_fixture_tree *left;
            const pep_fixture_tree *right;
        } pair;
    } as;
};

typedef struct {
    int64_t point_sum;
    int64_t tree_sum;
    int64_t list_sum;
    size_t utf8_len;
    pep_status overflow_status;
    pep_status invalid_tag_status;
    pep_status owner_mismatch_status;
    pep_status owner_recovery_status;
    size_t point_size;
    size_t point_align;
    size_t point_y_offset;
    size_t tree_size;
    size_t tree_align;
    size_t tree_payload_offset;
} pep_fixture_report;

pep_status pep_abi_fixture_run(pep_fixture_report *out);

#endif
