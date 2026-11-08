// t2_names — T2 self-check probe v3: v2 + trailing returns in the two
// loop-free classifiers (A1 v2 verdict: first refusal was missing trailing
// return). Loops contain ZERO conditionals: classification lives in
// helpers (is_fn_at, is_paren); loops only accumulate and advance.
// Pass 1 counts "fn " occurrences; pass 2 counts byte-40 '(' occurrences.
// main returns 0 = def+call present, 1 = no definition, 2 = no call.
// Fixed-shape probe, not a general lexer: matches exactly "fn " with one
// space; reports counts, never materialises names as Str.
// Expected: t2_valid 0, t2_nodef 1, t2_nocall 2.

fn is_fn_at(source: SourceBytes, o: Int) -> Int {
  var r = 0
  if byte_at(source, o) == 102 && byte_at(source, o + 1) == 110 && byte_at(source, o + 2) == 32 {
    r = 1
  } else {
  }
  return r
}

fn is_paren(byte: Int) -> Int {
  var r = 0
  if byte == 40 {
    r = 1
  } else {
  }
  return r
}

fn count_fn(source: SourceBytes) -> Int {
  var n = 0
  var o = 0
  var length = byte_length(source)
  while !(length <= o + 2) {
    n = n + is_fn_at(source, o)
    o = o + 1
  }
  return n
}

fn count_call(source: SourceBytes) -> Int {
  var n = 0
  var o = 0
  var length = byte_length(source)
  while !(length <= o) {
    n = n + is_paren(byte_at(source, o))
    o = o + 1
  }
  return n
}

fn main(source: SourceBytes) -> Int {
  var r = 0
  if count_fn(source) == 0 {
    r = 1
  } else {
  }
  if r == 0 {
    if count_call(source) == 0 {
      r = 2
    } else {
    }
  } else {
  }
  return r
}
