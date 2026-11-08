// A3-S1 differential fixture: exercises the three by-name byte lowerings that
// bea071a rewrote with prepend+reverse (byte_length, byte_at, utf8_slice).
// Kept deliberately small: one expression per function, assign-result plus a
// single trailing return, so the shape is emittable at BOTH pins.
fn a3_slice(source: SourceBytes, limit: Int) -> Str {
  return utf8_slice(source, 0, limit)
}

fn a3_first(source: SourceBytes) -> Int {
  return byte_at(source, 0)
}

fn a3_size(source: SourceBytes) -> Int {
  return byte_length(source)
}

fn main(source: SourceBytes) -> Int {
  let text = a3_slice(source, 3)
  say(text)
  let head = a3_first(source)
  let size = a3_size(source)
  return head
}