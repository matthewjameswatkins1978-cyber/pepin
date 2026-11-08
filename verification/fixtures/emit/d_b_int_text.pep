// A3-S1 differential fixture: int_text is the fourth lowering bea071a rewrote.
// Kept INLINE in main because a helper returning Str is refused cross-chunk at
// 1885566 (measured) - that limit is not what this audit is testing.
fn main(source: SourceBytes) -> Int {
  let size = byte_length(source)
  say(int_text(size))
  return size
}