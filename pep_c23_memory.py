"""The direct backend's private managed-storage and shadow-frame lowering."""

from pathlib import Path


RUNTIME = Path(__file__).resolve().parent / "runtime"
UNMANAGED_TYPES = {"int64_t", "bool", "void", "pep_source_bytes"}

SOURCE_VIEW_RUNTIME = r"""
/* Borrowed immutable bytes. The host keeps the backing alive for every use,
   including use of views returned from generated functions.
   The direct program does not obtain a source grant or open any path. */
typedef struct { const unsigned char *data; size_t length; } pep_source_bytes;

static inline void pep_validate_source_view(pep_source_bytes source)
{
    if (source.length > 65536) {
        fputs("PEP_SOURCE_BYTE_LIMIT: Source byte input exceeds 65536 bytes\n", stderr);
        exit(1);
    }
    if (source.length != 0 && source.data == nullptr) {
        fputs("PEP_RUNTIME_INVALID_SOURCE_BYTES: Source byte input has no backing\n", stderr);
        exit(1);
    }
}

static inline int64_t pep_byte_length(pep_source_bytes source)
{
    pep_validate_source_view(source);
    return (int64_t)source.length;
}

static inline int64_t pep_byte_at(pep_source_bytes source, int64_t offset)
{
    pep_validate_source_view(source);
    if (offset < 0 || (uintmax_t)offset >= source.length) {
        fputs("PEP_RUNTIME_BYTE_RANGE: Byte offset is outside the source\n", stderr);
        exit(1);
    }
    return source.data[(size_t)offset];
}

static inline pep_source_bytes pep_byte_slice(pep_source_bytes source, int64_t start, int64_t finish)
{
    pep_validate_source_view(source);
    if (start < 0 || finish < start || (uintmax_t)finish > source.length) {
        fputs("PEP_RUNTIME_BYTE_RANGE: Byte slice must be a valid half-open source range\n", stderr);
        exit(1);
    }
    const unsigned char *data = start == 0 ? source.data : source.data + (size_t)start;
    return (pep_source_bytes){data, (size_t)(finish - start)};
}
"""

UTF8_SLICE_RUNTIME = r"""
static inline pep_heap_object *pep_alloc_string(size_t bytes)
{
    pep_heap_object *owner = pep_heap_alloc_safepoint(&pep_native_heap, bytes, nullptr);
    if (owner == nullptr) {
        fputs("PEP_RUNTIME_ALLOC_FAILURE: String allocation failed\n", stderr);
        exit(1);
    }
    return owner;
}

static inline bool pep_utf8_boundary(pep_source_bytes source, size_t offset)
{
    return offset == 0 || offset == source.length || (source.data[offset] & 0xc0u) != 0x80u;
}

static inline pep_str_t pep_utf8_slice(pep_source_bytes source, int64_t start, int64_t finish)
{
    pep_validate_source_view(source);
    if (start < 0 || finish < start || (uintmax_t)finish > source.length) {
        fputs("PEP_RUNTIME_BYTE_RANGE: UTF-8 slice must be a valid half-open source range\n", stderr);
        exit(1);
    }
    if (!pep_utf8_boundary(source, (size_t)start) || !pep_utf8_boundary(source, (size_t)finish)) {
        fputs("PEP_RUNTIME_BYTE_BOUNDARY: UTF-8 slice boundary splits a UTF-8 sequence\n", stderr);
        exit(1);
    }
    size_t length = (size_t)(finish - start);
    if (length == 0) {
        return (pep_str_t){"", 0, nullptr};
    }
    const char *selected = (const char *)source.data + (size_t)start;
    size_t invalid = 0;
    if (pep_utf8_validate(selected, length, &invalid) != PEP_UTF8_OK) {
        fprintf(stderr, "PEP_RUNTIME_INVALID_UTF8: UTF-8 slice contains invalid encoding at byte %zu\n", invalid);
        exit(1);
    }
    // The Str can outlive the borrowed view or its caller's storage.
    pep_heap_object *owner = pep_alloc_string(length);
    char *data = pep_heap_data(owner);
    memcpy(data, selected, length);
    return (pep_str_t){data, length, owner};
}
"""


def trace_name(c_type):
    return f"pep_mark_{c_type}"


def has_references(c_type):
    return c_type not in UNMANAGED_TYPES


def constructor_tag(checked_id):
    # A zero-initialized root slot has no active union payload.
    return checked_id + 1


def _inline_runtime(stem):
    # --emit-c must produce a standalone translation unit.
    header = stem.with_suffix(".h").read_text(encoding="utf-8")
    implementation = stem.with_suffix(".c").read_text(encoding="utf-8")
    include = f'#include "{stem.name}.h"\n'
    return header + "\n" + implementation.replace(include, "", 1)


def runtime_source():
    return (_inline_runtime(RUNTIME / "pep_heap" / "pep_heap")
            + "\n" + _inline_runtime(RUNTIME / "pep_text" / "pep_utf8") + """
typedef struct {
    pep_heap_roots mark;
    void *address;
} pep_root_slot;

typedef struct {
    const pep_root_slot *slots;
    size_t count;
} pep_root_slots;

static pep_heap pep_native_heap;

static void pep_mark_slots(pep_heap_marker *marker, void *context)
{
    const pep_root_slots *roots = context;
    for (size_t i = 0; i < roots->count; ++i) {
        roots->slots[i].mark(marker, roots->slots[i].address);
    }
}

static void pep_destroy_native_heap(void)
{
    pep_heap_destroy(&pep_native_heap);
}
""")


class RootFrame:
    def __init__(self):
        self.slots = {}
        self.temporaries = []
        self.locals = []
        self.loop_scopes = []

    def track(self, name, c_type, *, declare=False):
        if not has_references(c_type):
            return False
        self.slots[name] = (c_type, declare)
        return True

    def track_temporary(self, name, c_type):
        if not self.track(name, c_type, declare=True):
            return False
        self.temporaries.append(name)
        return True

    def track_local(self, name, c_type):
        if not self.track(name, c_type, declare=True):
            return False
        self.locals.append(name)
        return True

    def clear_slots(self, names):
        return [f"{name} = ({self.slots[name][0]}){{0}}" for name in names]

    def clear_temporaries(self, checkpoint):
        return self.clear_slots(self.temporaries[checkpoint:])

    def clear_locals(self, checkpoint, indent):
        return [f"{indent}{clear};" for clear in self.clear_slots(self.locals[checkpoint:])]

    def enter(self):
        lines = [
            "  pep_heap_frame pep_roots;",
            f"  const bool pep_has_roots = {'true' if self.slots else 'false'};",
        ]
        if self.slots:
            lines.extend(f"  {c_type} {name} = {{0}};"
                         for name, (c_type, declare) in self.slots.items() if declare)
            lines.append("  const pep_root_slot pep_slots[] = {")
            lines.extend(f"    {{ {trace_name(c_type)}, &{name} }},"
                         for name, (c_type, _) in self.slots.items())
            lines.extend([
                "  };",
                "  pep_root_slots pep_slot_set = { pep_slots, sizeof pep_slots / sizeof *pep_slots };",
                "  pep_heap_push_frame(&pep_native_heap, &pep_roots, pep_mark_slots, &pep_slot_set);",
            ])
        return lines

    def leave(self, indent):
        return f"{indent}if (pep_has_roots) pep_heap_pop_frame(&pep_native_heap, &pep_roots);"

    def lower_return(self, c_type, value, indent):
        if c_type == "void":
            return [f"{indent}{value};", self.leave(indent), f"{indent}return;"]
        # The result is fully evaluated before unlinking its frame. The caller
        # consumes or publishes it before any further managed allocation.
        inner = indent + "  "
        return [
            f"{indent}{{",
            f"{inner}{c_type} pep_return_value = {value};",
            self.leave(inner),
            f"{inner}return pep_return_value;",
            f"{indent}}}",
        ]


def _trace_fields(fields):
    return [f"{trace_name(c_type)}(marker, &value->{member});"
            for c_type, member in fields if has_references(c_type)]


def trace_layouts(records, unions, lists, emit_type):
    """Generate exact walkers for C descriptors and active aggregate members."""
    descriptor_body = ["pep_heap_mark(marker, value->owner);"]
    bodies = {"pep_str_t": descriptor_body}
    for list_type, _, _ in lists.values():
        bodies[list_type] = descriptor_body
    for name, record in records.items():
        fields = [(emit_type(field["type"]), field["name"]) for field in record["fields"]]
        bodies[f"pep_rec_{name}"] = _trace_fields(fields)
    for name, union in unions.items():
        cases = []
        for variant in union["variants"]:
            fields = [(emit_type(arg), f"val.{variant['name']}._{i}")
                      for i, arg in enumerate(variant["arguments"])]
            visits = _trace_fields(fields)
            if visits:
                cases.append(f"  case {constructor_tag(variant['constructorId'])}:")
                cases.extend(f"    {visit}" for visit in visits)
                cases.append("    break;")
        bodies[f"pep_union_{name}"] = [
            "switch (value->tag) {", *cases, "  default: break;", "}",
        ] if cases else []

    lines = [f"static void {trace_name(c_type)}(pep_heap_marker *, void *);" for c_type in bodies]
    for c_type, body in bodies.items():
        lines.append(f"static void {trace_name(c_type)}(pep_heap_marker *marker, void *context) {{")
        if body:
            lines.append(f"  {c_type} *value = context;")
            lines.extend(f"  {line}" for line in body)
        else:
            lines.append("  (void)marker; (void)context;")
        lines.append("}")

    for prefix, (_, item_type, _) in lists.items():
        if has_references(item_type):
            lines.extend([
                f"static void {prefix}mark_items(pep_heap_marker *marker, pep_heap_object *owner) {{",
                f"  {item_type} *items = pep_heap_data(owner);",
                "  size_t len = pep_heap_size(owner) / sizeof *items;",
                f"  for (size_t i = 0; i < len; ++i) {trace_name(item_type)}(marker, &items[i]);",
                "}",
            ])
    return lines
