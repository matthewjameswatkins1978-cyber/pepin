// A3-S1 control: a literal non-zero, non-minus-one divisor is genuinely
// infallible (pep_div only aborts on b==0, or a==INT64_MIN && b==-1),
// so treating `/ 5` as infallible is CORRECT. Contrast with d_d (variable divisor).
fn main(source: SourceBytes) -> Int {
  let size = byte_length(source)
  let x = size / size + size / 5
  return x
}