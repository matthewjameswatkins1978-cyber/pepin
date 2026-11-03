// Length-aware text building for compiler output.
//
// The emitter's own output is a `List[Str]` that the host joins, and the host is the only place that
// can currently count the resulting bytes. This module makes the byte count part of the value, so a
// consumer can report exact output width without joining anything.
//
// Why the caller supplies the width: the Pep seed has no `Str` length and no `Str` -> bytes
// conversion, and `Str + Str` is not supported. The builtin inventory is `say`, `int_text`,
// `length`, `append`, `prepend`, `reverse`, `contains`, `byte_length`, `byte_at`, `byte_slice`,
// `utf8_slice`, `semantic_snapshot`, `source_bytes`. So a fragment's UTF-8 width is knowable only by
// the caller -- a hand-counted ASCII literal, or a source span, which `text_builder_push_span`
// derives exactly and which is why that entry point exists rather than a `text_builder_push_str`.

type TextBuilder {
  parts: List[Str],
  partCount: Int,
  byteCount: Int
}

fn text_builder_new() -> TextBuilder {
  return TextBuilder { parts: [], partCount: 0, byteCount: 0 }
}

fn text_builder_is_empty(builder: TextBuilder) -> Bool {
  return builder.partCount == 0
}

fn text_builder_bytes(builder: TextBuilder) -> Int {
  return builder.byteCount
}

fn text_builder_part_count(builder: TextBuilder) -> Int {
  return builder.partCount
}

// The parts in source order, ready to be joined by the host. This is the same shape the C23 emitter
// already hands back, so a consumer can reuse its emission path.
fn text_builder_parts(builder: TextBuilder) -> List[Str] {
  return builder.parts
}

// Append a fragment whose UTF-8 width the caller knows exactly. A negative width is refused by
// returning the builder unchanged rather than letting the byte count run backwards; a caller that
// cares checks `text_builder_part_count` grew.
fn text_builder_push(builder: TextBuilder, fragment: Str, width: Int) -> TextBuilder {
  if !(0 <= width) { return builder } else {}
  return TextBuilder {
    parts: append(builder.parts, fragment),
    partCount: builder.partCount + 1,
    byteCount: builder.byteCount + width
  }
}

// Append the source bytes between two offsets. The width comes from the span, so UTF-8 multi-byte
// text and embedded NUL bytes are counted exactly without the caller measuring anything.
fn text_builder_push_span(builder: TextBuilder, source: SourceBytes, start: Int, end: Int) -> TextBuilder {
  if !(start <= end) { return builder } else {}
  return text_builder_push(builder, utf8_slice(source, start, end), end - start)
}
