// A3-S1 probe for b758c91 (arithmetic may_fail = OR(operands)).
// pep_div ABORTS at runtime when the divisor is 0, so `/` with a VARIABLE
// divisor is not infallible. If may_fail now says it is, this expression stops
// being refused and is emitted with unspecified C operand evaluation order.
fn main(source: SourceBytes) -> Int {
  let size = byte_length(source)
  let x = size / size + size / 1
  return x
}