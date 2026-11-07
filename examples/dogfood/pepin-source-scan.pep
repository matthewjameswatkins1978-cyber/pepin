// pepin-source-scan — A4 dogfood application (grammar truth lane).
// Counts identifier-start runs in the granted SourceBytes document.
// Identifier-start  := ascii_letter(byte) is true.
// New run           := start at offset 0, or previous byte is NOT ascii_continue.
// Uses only the already-proven lexer predicates verbatim from examples/pep_lexer.pep.
// Result is an Int (number of runs); no token text is returned (output-contract limit).
// Non-ASCII bytes never start or continue a run; empty input returns 0.

fn ascii_letter(byte: Int) -> Bool {
  return (65 <= byte && byte <= 90) || (97 <= byte && byte <= 122) || byte == 95
}

fn ascii_digit(byte: Int) -> Bool {
  return 48 <= byte && byte <= 57
}

fn ascii_continue(byte: Int) -> Bool {
  return ascii_letter(byte) || ascii_digit(byte)
}

fn main(source: SourceBytes) -> Int {
  var n = 0
  var o = 0
  while !(byte_length(source) <= o) {
    if ascii_letter(byte_at(source, o)) {
      if o == 0 {
        n = n + 1
      } else {
        if ascii_continue(byte_at(source, o - 1)) {
        } else {
          n = n + 1
        }
      }
    } else {
    }
    o = o + 1
  }
  return n
}
