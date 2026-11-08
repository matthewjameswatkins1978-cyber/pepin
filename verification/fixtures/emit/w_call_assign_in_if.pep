// A3 reproducer: cross-chunk call as the RHS of an assignment inside an if body.
// Whole-function emission is expected to work; the statement FRAGMENT path is the
// one that refuses with "Pep C23 calls require a known target" (A3-120).
fn a3_take(n: Int) -> Int {
  return n + 1
}

fn a3_assign_in_if(source: SourceBytes) -> Int {
  var e = 0
  let n = byte_length(source)
  if n == 4 {
    e = a3_take(n)
  } else {
  }
  return e
}