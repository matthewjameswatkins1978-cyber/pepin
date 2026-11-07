// A3 BOOT-A3-053: decomposed version of A4's T2 names probe, testing whether the two fixes
// A3 recommended in BOOT-A3-052 actually make it emittable. Semantics are identical.
//   (1) the three-byte "fn " test moved into a small loop-free helper
//   (2) every function uses assign-result + ONE reachable trailing return
// Result contract unchanged: 0 = def+call present, 1 = no definition, 2 = no call.

fn is_fn_at(source: SourceBytes, o: Int) -> Bool {
  var r = false
  if byte_at(source, o) == 102 {
    if byte_at(source, o + 1) == 110 {
      if byte_at(source, o + 2) == 32 { r = true } else { }
    } else { }
  } else { }
  return r
}

fn find_fn(source: SourceBytes) -> Int {
  var o = 0
  var length = byte_length(source)
  while !(length <= o + 2) {
    if is_fn_at(source, o) {
      return o + 3
    } else {
      o = o + 1
    }
  }
  return 0 - 1
}

fn find_call(source: SourceBytes) -> Int {
  var o = 0
  var length = byte_length(source)
  while !(length <= o) {
    if byte_at(source, o) == 40 {
      return o
    } else {
      o = o + 1
    }
  }
  return 0 - 1
}

fn main(source: SourceBytes) -> Int {
  var r = 0
  let none = 0 - 1
  if find_fn(source) == none {
    r = 1
  } else {
    if find_call(source) == none { r = 2 } else { r = 0 }
  }
  return r
}
