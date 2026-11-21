#include "pep_heap.h"

#include <stdint.h>
#include <stdlib.h>

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

pep_heap_object *pep_heap_alloc(pep_heap *heap, size_t size, pep_heap_trace trace)
{
    if (size == 0 || size > SIZE_MAX - sizeof(pep_heap_object)
        || size > SIZE_MAX - heap->live_bytes) {
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
}

void pep_heap_destroy(pep_heap *heap)
{
    pep_heap_collect(heap, nullptr, nullptr);
}
