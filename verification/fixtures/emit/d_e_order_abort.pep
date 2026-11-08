// A3-S1: minimal reproducer for the b758c91 fallibility hole.
// Left operand aborts with PEP_RUNTIME_DIVISION_BY_ZERO (gap == 0),
// right operand aborts with PEP_RUNTIME_OVERFLOW (size >= 1).
// Their order inside one `+` is unspecified in C, so WHICH message appears
// is unspecified. The 1885566 guard refused exactly this shape.
fn main(source: SourceBytes) -> Int {
  let size = byte_length(source)
  let gap = size - size
  let x = size / gap + (size + 9223372036854775807)
  return x
}