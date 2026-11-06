// C declaration fragments built on stdlib/text_builder.pep.
//
// This is a consumer, not a probe. The C23 emitter emits the same single-line shape
// (`typedef struct { … } pep_record_<name>;`) but with `pep_field_<index>` members, so this module
// gives a caller a readable declaration with named fields. It is deliberately NOT emitter-identical:
// where the emitter's exact bytes matter, call the emitter instead of rebuilding them here.
// Every fragment is newline-free so a caller decides layout; the builder tracks the byte total.
//
// Widths are literal counts because the seed cannot measure a `Str` (no length, no Str -> bytes, no
// `Str + Str`). tests/test_text_builder.py asserts the composed byte total against the real joined
// width, which is how a wrong count gets caught rather than shipped.

fn c_open_record(builder: TextBuilder, name: Str, nameBytes: Int) -> TextBuilder {
  var next = builder
  next = text_builder_push(next, "typedef struct pep_record_", 26)
  next = text_builder_push(next, name, nameBytes)
  next = text_builder_push(next, " { ", 3)
  return next
}

fn c_record_field(builder: TextBuilder, typeText: Str, typeBytes: Int, name: Str, nameBytes: Int) -> TextBuilder {
  var next = builder
  next = text_builder_push(next, typeText, typeBytes)
  next = text_builder_push(next, " ", 1)
  next = text_builder_push(next, name, nameBytes)
  next = text_builder_push(next, "; ", 2)
  return next
}

fn c_close_record(builder: TextBuilder, name: Str, nameBytes: Int) -> TextBuilder {
  var next = builder
  next = text_builder_push(next, "} pep_record_", 13)
  next = text_builder_push(next, name, nameBytes)
  next = text_builder_push(next, ";", 1)
  return next
}

// Convenience: a two-Int-field record declaration, the shape that dominates current generated C.
fn c_two_int_record(name: Str, nameBytes: Int, first: Str, firstBytes: Int, second: Str, secondBytes: Int) -> TextBuilder {
  var next = c_open_record(text_builder_new(), name, nameBytes)
  next = c_record_field(next, "int64_t", 7, first, firstBytes)
  next = c_record_field(next, "int64_t", 7, second, secondBytes)
  return c_close_record(next, name, nameBytes)
}
