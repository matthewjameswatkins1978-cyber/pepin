// A3-S1 differential fixture: int_text is the fourth lowering bea071a rewrote.
// Isolated in its own program because it may not emit at the 1885566 baseline;
// separating it keeps a refusal on int_text from masking the byte lowerings.
fn a3_label(count: Int) -> Str {
  return int_text(count)
}

fn main(source: SourceBytes) -> Int {
  let size = byte_length(source)
  let text = a3_label(size)
  say(text)
  return size
}