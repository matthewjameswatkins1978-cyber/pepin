// A3-S1 differential fixture: the binary/arithmetic lowering a38a91e rewrote
// with prepend+reverse, plus the shapes b758c91 declared fallible-by-OR.
fn a3_sum(a: Int, b: Int) -> Int {
  return a + b
}

fn a3_scale(a: Int) -> Int {
  return a * 3
}

fn a3_le(a: Int, b: Int) -> Bool {
  return a <= b
}

fn main(source: SourceBytes) -> Int {
  let size = byte_length(source)
  let doubled = a3_sum(size, size)
  let scaled = a3_scale(doubled)
  let small = a3_le(scaled, 64)
  return scaled
}