"""The direct backend's private managed-storage and shadow-frame lowering."""

from pathlib import Path


HEAP_SOURCE = Path(__file__).resolve().parent / "runtime" / "pep_heap"
SCALAR_TYPES = {"int64_t", "bool", "void"}


def trace_name(c_type):
    return f"pep_mark_{c_type}"


def has_references(c_type):
    return c_type not in SCALAR_TYPES


def constructor_tag(checked_id):
    # A zero-initialized root slot has no active union payload.
    return checked_id + 1


def runtime_source():
    # --emit-c must produce a standalone translation unit.
    header = (HEAP_SOURCE / "pep_heap.h").read_text(encoding="utf-8")
    implementation = (HEAP_SOURCE / "pep_heap.c").read_text(encoding="utf-8")
    implementation = implementation.replace('#include "pep_heap.h"\n', "", 1)
    return header + "\n" + implementation + """
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
"""


class RootFrame:
    def __init__(self):
        self.slots = {}

    def track(self, name, c_type, *, declare=False):
        if not has_references(c_type):
            return False
        self.slots[name] = (c_type, declare)
        return True

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
