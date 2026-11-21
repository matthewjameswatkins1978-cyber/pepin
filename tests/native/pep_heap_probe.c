#include "pep_heap.h"

#include <assert.h>
#include <stdint.h>
#include <stdlib.h>

static size_t allocations;
static size_t attempts;
static bool refuse;
static bool fail_once;

// Only the heap translation unit is compiled with these allocator overrides.
void *probe_malloc(size_t size)
{
    attempts++;
    void *allocation = (refuse || fail_once) ? nullptr : malloc(size);
    fail_once = false;
    allocations += allocation != nullptr;
    return allocation;
}

void probe_free(void *allocation)
{
    assert(allocation != nullptr && allocations > 0);
    allocations--;
    free(allocation);
}

typedef struct {
    pep_heap_object *first;
    pep_heap_object *second;
    size_t value;
} node;

static void trace_node(pep_heap_marker *marker, pep_heap_object *object)
{
    assert(pep_heap_size(object) == sizeof(node));
    const node *value = pep_heap_data(object);
    pep_heap_mark(marker, value->first);
    pep_heap_mark(marker, value->second);
}

static pep_heap_object *new_node(pep_heap *heap, node value)
{
    pep_heap_object *object = pep_heap_alloc(heap, sizeof value, trace_node);
    assert(object != nullptr);
    *(node *)pep_heap_data(object) = value;
    return object;
}

typedef struct {
    pep_heap_object *graph;
    pep_heap_object *owner;
    const unsigned char *view;
} roots;

static void trace_roots(pep_heap_marker *marker, void *context)
{
    const roots *root = context;
    pep_heap_mark(marker, root->graph);
    pep_heap_mark(marker, root->owner);
}

static void probe_safepoints(void)
{
    pep_heap heap = {.stress = true};
    roots caller = {0};
    roots callee = {0};
    pep_heap_frame outer;
    pep_heap_frame inner;
    pep_heap_push_frame(&heap, &outer, trace_roots, &caller);
    caller.owner = pep_heap_alloc_safepoint(&heap, 16, nullptr);
    assert(caller.owner != nullptr);
    unsigned char *bytes = pep_heap_data(caller.owner);
    bytes[3] = 7;
    caller.view = bytes + 3;

    pep_heap_push_frame(&heap, &inner, trace_roots, &callee);
    callee.graph = pep_heap_alloc_safepoint(&heap, sizeof(node), trace_node);
    assert(callee.graph != nullptr);
    *(node *)pep_heap_data(callee.graph) = (node){.first = caller.owner};
    caller.owner = nullptr;
    assert(pep_heap_alloc_safepoint(&heap, 8, nullptr) != nullptr);
    assert(heap.live_objects == 3 && *caller.view == 7);

    // Transfer the result across return without collecting between pop and publish.
    pep_heap_object *result = callee.graph;
    pep_heap_pop_frame(&heap, &inner);
    caller.graph = result;
    assert(pep_heap_alloc_safepoint(&heap, 8, nullptr) != nullptr);
    assert(heap.live_objects == 3 && *caller.view == 7);

    heap.stress = false;
    size_t before = attempts;
    fail_once = true;
    assert(pep_heap_alloc_safepoint(&heap, 8, nullptr) != nullptr);
    assert(attempts == before + 2 && heap.live_objects == 3);
    assert(*caller.view == 7);

    // An unrooted allocation loop must stay under the default threshold.
    for (size_t i = 0; i < 4096; i++) {
        assert(pep_heap_alloc_safepoint(&heap, 4096, nullptr) != nullptr);
        assert(heap.live_bytes <= 65536);
        assert(*caller.view == 7);
    }
    pep_heap_pop_frame(&heap, &outer);
    pep_heap_collect(&heap, nullptr, nullptr);
    assert(allocations == 0 && heap.live_objects == 0);
    pep_heap_destroy(&heap);
}

int main(void)
{
    pep_heap heap = {0};
    pep_heap other = {0};
    enum { depth = 100000, samples = 4096 };

    roots root = {0};
    root.owner = pep_heap_alloc(&heap, 16, nullptr);
    assert(root.owner != nullptr);
    unsigned char *bytes = pep_heap_data(root.owner);
    assert((uintptr_t)bytes % alignof(max_align_t) == 0);
    assert(pep_heap_size(root.owner) == 16);
    bytes[9] = 0x6A;
    root.view = bytes + 9;

    pep_heap_object *tail = new_node(&heap, (node){ .value = depth });
    root.graph = tail;
    for (size_t i = depth; i > 0; i--) {
        root.graph = new_node(&heap, (node){root.graph, tail, i - 1});
    }
    node *last = pep_heap_data(tail);
    last->first = root.graph;
    pep_heap_object *dead = new_node(&heap, (node){0});
    ((node *)pep_heap_data(dead))->first = dead;
    assert(pep_heap_alloc(&other, 8, nullptr) != nullptr);
    assert(heap.live_objects == depth + 3);

    refuse = true;
    assert(pep_heap_alloc(&heap, 8, nullptr) == nullptr);
    size_t before = attempts;
    assert(pep_heap_alloc(&heap, SIZE_MAX, nullptr) == nullptr);
    assert(pep_heap_alloc(&heap, 0, nullptr) == nullptr);
    assert(attempts == before && heap.live_objects == depth + 3);
    pep_heap_collect(&heap, trace_roots, &root);
    assert(attempts == before && heap.live_objects == depth + 2);
    assert(other.live_objects == 1 && *root.view == 0x6A);
    assert(heap.live_bytes == (depth + 1) * sizeof(node) + 16);

    pep_heap_object *cursor = root.graph;
    for (size_t i = 0; i <= depth; i++) {
        const node *value = pep_heap_data(cursor);
        assert(value->value == i);
        cursor = value->first;
    }
    assert(cursor == root.graph);
    root.graph = nullptr;
    pep_heap_collect(&heap, trace_roots, &root);
    assert(heap.live_objects == 1 && heap.live_bytes == 16);

    refuse = false;
    for (size_t i = 0; i < samples; i++) {
        assert(pep_heap_alloc(&heap, 4096, nullptr) != nullptr);
        pep_heap_collect(&heap, trace_roots, &root);
        assert(heap.live_bytes == 16 && *root.view == 0x6A);
        assert(allocations == 2);
    }
    pep_heap_destroy(&heap);
    pep_heap_destroy(&heap);
    assert(allocations == 1 && heap.live_objects == 0 && heap.live_bytes == 0);
    assert(pep_heap_alloc(&heap, 1, nullptr) != nullptr);
    pep_heap_destroy(&heap);
    pep_heap_destroy(&other);
    assert(allocations == 0);
    probe_safepoints();
}
