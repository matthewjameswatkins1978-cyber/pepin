// cursor_kind_v2 — T2 cursor primitive, whitespace + //-comment skip
// (LUCY-20261107-013 P2). first significant byte: 1 = name-start,
// 2 = digit-start, 3 = other byte, 0 = end (empty or only ws/comments).
// Expected: input_ascii 1, input_nonascii 1, input_empty 0,
// pepin-source-scan 1, pepin-line-scan 1. The v1->v2 delta (3->1 on
// //-leading files, others unchanged) is the comment rule's signature.

fn ascii_letter(byte: Int) -> Bool {
  return (65 <= byte && byte <= 90) || (97 <= byte && byte <= 122) || byte == 95
}

fn ascii_digit(byte: Int) -> Bool {
  return 48 <= byte && byte <= 57
}

fn first_kind(source: SourceBytes) -> Int {
  var o = 0
  var length = byte_length(source)
  while !(length <= o) {
    let b = byte_at(source, o)
    if b == 32 || b == 9 || b == 10 || b == 13 {
      o = o + 1
    } else {
      if b == 47 && !(length <= o + 1) && byte_at(source, o + 1) == 47 {
        while !(length <= o) && byte_at(source, o) != 10 {
          o = o + 1
        }
      } else {
        if ascii_letter(b) {
          return 1
        } else {
          if ascii_digit(b) {
            return 2
          } else {
            return 3
          }
        }
      }
    }
  }
  return 0
}

fn main(source: SourceBytes) -> Int {
  return first_kind(source)
}
