// A3-S1 differential fixture: exercises the three by-name byte lowerings that
// bea071a rewrote with prepend+reverse (byte_at, byte_length, utf8_slice).
// The Str-returning lowering stays INLINE in main: a helper returning Str is
// refused cross-chunk ("cross-chunk calls support Int, Bool, and locally
// declared record results"), measured at 1885566. Int-returning helpers are fine.
fn a3_first(source: SourceBytes, offset: Int) -> Int {
  return byte_at(source, offset)
}

fn a3_size(source: SourceBytes) -> Int {
  return byte_length(source)
}

fn main(source: SourceBytes) -> Int {
  let text = utf8_slice(source, 0, 3)
  say(text)
  let head = a3_first(source, 0)
  let size = a3_size(source)
  return head
}