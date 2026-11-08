// A3-S1 control: ONE fallible operand is fine (no ordering choice exists),
// so this must emit at BOTH pins. Isolates the regression to the two-operand case.
fn main(source: SourceBytes) -> Int {
  let size = byte_length(source)
  let gap = size - size
  let x = size / gap
  return x
}