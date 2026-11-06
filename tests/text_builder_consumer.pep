// A compiler-shaped consumer of stdlib/text_builder.pep: emit one C record typedef line.
//
// Widths are hand-counted ASCII literals here because `pep.ps1 run` has no SourceBytes context
// (`source_bytes()` is host-authorised only), so a span-based probe cannot run interpreted. The
// span entry point is exercised through the tool host instead, where that context exists.
//
// Pep has no imports yet, so tests/test_text_builder.py concatenates this file with the module, and
// `pep.ps1 run` executes the top-level statements below (a run executes statements, not `main`).

fn emit_record_typedef(name: Str, nameBytes: Int, field: Str, fieldBytes: Int) -> TextBuilder {
  var builder = text_builder_new()
  builder = text_builder_push(builder, "typedef struct pep_record_", 26)
  builder = text_builder_push(builder, name, nameBytes)
  builder = text_builder_push(builder, " { int64_t ", 11)
  builder = text_builder_push(builder, field, fieldBytes)
  builder = text_builder_push(builder, "; } pep_record_", 15)
  builder = text_builder_push(builder, name, nameBytes)
  builder = text_builder_push(builder, ";\n", 2)
  return builder
}

let demo = emit_record_typedef("ab", 2, "value", 5)
say(int_text(text_builder_bytes(demo)))
say(int_text(text_builder_part_count(demo)))
for part in text_builder_parts(demo) { say(part) }
