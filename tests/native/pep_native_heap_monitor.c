#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#ifndef PEP_PROBE_FAIL_AT
#define PEP_PROBE_FAIL_AT SIZE_MAX
#endif

typedef struct {
    alignas(max_align_t) size_t bytes;
} allocation_header;

static size_t calls;
static size_t live;
static size_t peak;

void *probe_malloc(size_t bytes)
{
    if (++calls >= PEP_PROBE_FAIL_AT || bytes > SIZE_MAX - sizeof(allocation_header)) {
        return nullptr;
    }
    allocation_header *header = malloc(sizeof *header + bytes);
    if (header == nullptr) {
        return nullptr;
    }
    header->bytes = bytes;
    live += bytes;
    if (live > peak) {
        peak = live;
    }
    return header + 1;
}

void probe_free(void *allocation)
{
    assert(allocation != nullptr);
    allocation_header *header = (allocation_header *)allocation - 1;
    assert(live >= header->bytes);
    live -= header->bytes;
    free(header);
}

static void report(void)
{
    fprintf(stderr, "heap live=%zu peak=%zu calls=%zu\n", live, peak, calls);
}

int pep_test_program(int argc, char **argv);

int main(int argc, char **argv)
{
    // The generated program registers its cleanup after this callback, so
    // accounting is read after every managed object has been freed.
    if (atexit(report) != 0) {
        return 2;
    }
    return pep_test_program(argc, argv);
}
