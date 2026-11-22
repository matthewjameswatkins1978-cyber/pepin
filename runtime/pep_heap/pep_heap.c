#include "pep_heap.h"

#include <assert.h>
#include <stdint.h>
#include <stdlib.h>

#define PEP_HEAP_MIN_COLLECTION ((size_t)65536)

struct pep_heap_object {
    alignas(max_align_t) pep_heap_object *next;
    pep_heap_object *pending;
    pep_heap_trace trace;
    size_t size;
    bool marked;
};

struct pep_heap_marker {
    pep_heap_object *pending;
};

static size_t allocated_bytes(const pep_heap *heap)
{
    return heap->live_bytes + heap->live_objects * sizeof(pep_heap_object);
}

pep_heap_object *pep_heap_alloc(pep_heap *heap, size_t size, pep_heap_trace trace)
{
    if (size == 0 || size > SIZE_MAX - sizeof(pep_heap_object)
        || size + sizeof(pep_heap_object) > SIZE_MAX - allocated_bytes(heap)) {
        return nullptr;
    }
    pep_heap_object *object = malloc(sizeof *object + size);
    if (object == nullptr) {
        return nullptr;
    }
    *object = (pep_heap_object){
        .next = heap->objects,
        .trace = trace,
        .size = size,
    };
    heap->objects = object;
    heap->live_bytes += size;
    heap->live_objects++;
    return object;
}

void *pep_heap_data(pep_heap_object *object)
{
    return object + 1;
}

size_t pep_heap_size(const pep_heap_object *object)
{
    return object->size;
}

void pep_heap_push_frame(pep_heap *heap, pep_heap_frame *frame,
                         pep_heap_roots trace, void *context)
{
    *frame = (pep_heap_frame){heap->frames, trace, context};
    heap->frames = frame;
}

void pep_heap_pop_frame(pep_heap *heap, pep_heap_frame *frame)
{
    assert(heap->frames == frame);
    heap->frames = frame->previous;
}

void pep_heap_mark(pep_heap_marker *marker, pep_heap_object *object)
{
    if (object != nullptr && !object->marked) {
        object->marked = true;
        object->pending = marker->pending;
        marker->pending = object;
    }
}

void pep_heap_collect(pep_heap *heap, pep_heap_roots roots, void *context)
{
    pep_heap_marker marker = {0};
    if (roots != nullptr) {
        roots(&marker, context);
    }
    for (const pep_heap_frame *frame = heap->frames; frame != nullptr;
         frame = frame->previous) {
        frame->trace(&marker, frame->context);
    }
    while (marker.pending != nullptr) {
        pep_heap_object *object = marker.pending;
        marker.pending = object->pending;
        object->pending = nullptr;
        if (object->trace != nullptr) {
            object->trace(&marker, object);
        }
    }

    pep_heap_object **link = &heap->objects;
    while (*link != nullptr) {
        pep_heap_object *object = *link;
        if (object->marked) {
            object->marked = false;
            link = &object->next;
        } else {
            *link = object->next;
            heap->live_bytes -= object->size;
            heap->live_objects--;
            free(object);
        }
    }
    size_t live = allocated_bytes(heap);
    heap->next_collection = live > SIZE_MAX / 2 ? SIZE_MAX : live * 2;
    if (heap->next_collection < PEP_HEAP_MIN_COLLECTION) {
        heap->next_collection = PEP_HEAP_MIN_COLLECTION;
    }
}

pep_heap_object *pep_heap_alloc_safepoint(pep_heap *heap, size_t size,
                                          pep_heap_trace trace)
{
    if (size == 0 || size > SIZE_MAX - sizeof(pep_heap_object)) {
        return nullptr;
    }
    size_t live = allocated_bytes(heap);
    size_t limit = heap->next_collection ? heap->next_collection : PEP_HEAP_MIN_COLLECTION;
    bool collect_first = heap->stress
        || (live != 0 && (live >= limit || size + sizeof(pep_heap_object) > limit - live));
    if (collect_first) {
        pep_heap_collect(heap, nullptr, nullptr);
    }
    pep_heap_object *object = pep_heap_alloc(heap, size, trace);
    if (object == nullptr && !collect_first && live != 0) {
        pep_heap_collect(heap, nullptr, nullptr);
        object = pep_heap_alloc(heap, size, trace);
    }
    return object;
}

void pep_heap_destroy(pep_heap *heap)
{
    while (heap->objects != nullptr) {
        pep_heap_object *object = heap->objects;
        heap->objects = object->next;
        free(object);
    }
    *heap = (pep_heap){0};
}
