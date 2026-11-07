// t2_names — T2 self-check probe, Phase E follow-up (LUCY-20261107-013 P2).
// Pass 1 (signature scan): offset just past first "fn ", or -1.
// Pass 2 (use scan): offset of first byte 40 '(' (call paren), or -1.
// main returns 0 = def+call present, 1 = no definition, 2 = no call.
// Fixed-shape probe, not a general lexer: matches exactly "fn " with one
// space; reports offsets, never materialises names as Str.
// Expected: t2_valid 0, t2_nodef 1, t2_nocall 2.

fn ascii_letter(byte: Int) -> Bool {
  return (65 <= byte && byte <= 90) || (97 <= byte && byte <= 122) || byte == 95
}

fn find_fn(source: SourceBytes) -> Int {
  var o = 0
  var length = byte_length(source)
  while !(length <= o + 2) {
    if byte_at(source, o) == 102 && byte_at(source, o + 1) == 110 && byte_at(source, o + 2) == 32 {
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
  if find_fn(source) == 0 - 1 {
    return 1
  } else {
    if find_call(source) == 0 - 1 {
      return 2
    } else {
      return 0
    }
  }
}
