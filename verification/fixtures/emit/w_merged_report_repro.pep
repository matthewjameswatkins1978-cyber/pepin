// A3 minimal reproducer for two open fragment issues, 2 functions / 11 statements.
// Emit a3_t through A1's chain path (59 nodes forces chain-11) and sweep fragments:
//   stmts 2-7  `if e == N { e = N }`        -> "loop assignments must target a direct
//                                              mutable local"   (missing bindings, A3-117/120)
//   stmt  8    `var v = a3_small(n)`        -> EMITS
//   stmt  9    `if n == 4 { e = a3_small(n) }` -> "calls require a known target"
// Same callee, same merged report, both positions: initialiser emits, assignment-in-if
// refuses. With a whole-program report (small caller) both positions emit.
fn a3_small(a: Int) -> Int {
  return a
}

fn a3_t(source: SourceBytes) -> Int {
  var e = 0
  let n = byte_length(source)
  if e == 1 {
    e = 1
  } else {
  }
  if e == 2 {
    e = 2
  } else {
  }
  if e == 3 {
    e = 3
  } else {
  }
  if e == 4 {
    e = 4
  } else {
  }
  if e == 5 {
    e = 5
  } else {
  }
  if e == 6 {
    e = 6
  } else {
  }
  var v = a3_small(n)
  if n == 4 {
    e = a3_small(n)
  } else {
  }
  return e + v
}