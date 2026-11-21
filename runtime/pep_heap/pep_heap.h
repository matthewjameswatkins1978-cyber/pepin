#ifndef PEP_HEAP_H
#define PEP_HEAP_H

#include <stddef.h>

typedef struct pep_heap_object pep_heap_object;
typedef struct pep_heap_marker pep_heap_marker;
typedef void (*pep_heap_trace)(pep_heap_marker *, pep_heap_object *);
typedef void (*pep_heap_roots)(pep_heap_marker *, void *context);

typedef struct pep_heap_frame {
    struct pep_heap_frame *previous;
    pep_heap_roots trace;
    void *context;
} pep_heap_frame;

typedef struct {
    pep_heap_object *objects;
    pep_heap_frame *frames;
    size_t live_bytes;
    size_t live_objects;
    size_t next_collection;
    bool stress;
} pep_heap;

// Start with pep_heap heap = {0}. One thread owns each heap.
// Allocations have fundamental alignment and stable addresses. NULL means
// an invalid size, overflow or host allocation failure; the heap is intact.
// Allocation never collects. Initialise the payload before publishing the
// object to a root or live object. A NULL trace denotes a leaf object.
pep_heap_object *pep_heap_alloc(pep_heap *heap, size_t size, pep_heap_trace trace);
void *pep_heap_data(pep_heap_object *object);
size_t pep_heap_size(const pep_heap_object *object);

// Frames are caller-owned and pop in reverse order. Publish initialised
// roots before push, keep the context valid until pop, and pop before return.
void pep_heap_push_frame(pep_heap *heap, pep_heap_frame *frame,
                         pep_heap_roots trace, void *context);
void pep_heap_pop_frame(pep_heap *heap, pep_heap_frame *frame);

// Call at a safe point after publishing every live reference. Enumerate exact
// object handles (NULL is allowed); for any interior reference visit its
// owner. Collection visits registered frames and the optional extra roots.
// A trace callback can read the object's payload and size.
// Each non-NULL handle must be live in this heap. Callbacks may only inspect
// roots/payloads and mark handles. The marker is valid only during collection.
void pep_heap_mark(pep_heap_marker *marker, pep_heap_object *object);
void pep_heap_collect(pep_heap *heap, pep_heap_roots roots, void *context);

// Collect before allocation above the adaptive byte threshold, on allocation
// failure before retrying once, or before every allocation if heap.stress.
// All live roots must be visible in frames. The returned object is unrooted.
pep_heap_object *pep_heap_alloc_safepoint(pep_heap *heap, size_t size,
                                          pep_heap_trace trace);

// Release all objects without visiting frames, then reset the heap.
void pep_heap_destroy(pep_heap *heap);

#endif
