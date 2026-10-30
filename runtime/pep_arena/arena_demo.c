// Agent-4 arena demo: a real recursive expression program built entirely
// from arena-allocated nodes. The tree for `19 + 23` is three linked
// nodes; a nested `(1 + (2 + 3))` exercises deeper nesting and reuse of
// earlier pointers across chunk growth (small initial chunk forces
// several chunks, proving pointers stay valid). Prints each result and
// exits non-zero on any mismatch, allocation failure, or leak of the
// pattern (every node freed by one whole-arena release).
#include <stdint.h>
#include <stdio.h>

#include "pep_arena.h"

typedef enum {
    EX_INT,
    EX_ADD
} ex_kind_t;

typedef struct Expr Expr;

struct Expr {
    ex_kind_t kind;
    int64_t value;
    const Expr *left;
    const Expr *right;
};

static Expr *ex_int(pep_arena_t *arena, int64_t value)
{
    Expr *node = (Expr *)pep_arena_alloc(arena, sizeof *node, _Alignof(Expr));
    if (node == nullptr) {
        return nullptr;
    }
    node->kind = EX_INT;
    node->value = value;
    node->left = nullptr;
    node->right = nullptr;
    return node;
}

static Expr *ex_add(pep_arena_t *arena, const Expr *left, const Expr *right)
{
    Expr *node = (Expr *)pep_arena_alloc(arena, sizeof *node, _Alignof(Expr));
    if (node == nullptr) {
        return nullptr;
    }
    node->kind = EX_ADD;
    node->value = 0;
    node->left = left;
    node->right = right;
    return node;
}

static int ex_eval(const Expr *node, int64_t *out)
{
    int64_t left;
    int64_t right;
    if (node == nullptr || out == nullptr) {
        return 1;
    }
    if (node->kind == EX_INT) {
        *out = node->value;
        return 0;
    }
    if (node->left == nullptr || node->right == nullptr) {
        return 1;
    }
    if (ex_eval(node->left, &left) != 0 || ex_eval(node->right, &right) != 0) {
        return 1;
    }
    *out = left + right;
    return 0;
}

int main(void)
{
    pep_arena_t *arena = nullptr;
    const Expr *sum;
    const Expr *nested;
    int64_t answer = 0;
    int64_t nested_answer = 0;
    if (pep_arena_init(&arena, 64) != PEP_ARENA_OK) {
        return 1;
    }
    sum = ex_add(arena,
        ex_int(arena, 19),
        ex_int(arena, 23));
    nested = ex_add(arena,
        ex_int(arena, 1),
        ex_add(arena,
            ex_int(arena, 2),
            ex_int(arena, 3)));
    if (sum == nullptr || nested == nullptr ||
        ex_eval(sum, &answer) != 0 || ex_eval(nested, &nested_answer) != 0 ||
        answer != 42 || nested_answer != 6) {
        pep_arena_free(&arena);
        return 1;
    }
    (void)printf("%lld\n", (long long)answer);
    (void)printf("%lld\n", (long long)nested_answer);
    pep_arena_free(&arena);
    return (arena == nullptr) ? 0 : 1;
}
