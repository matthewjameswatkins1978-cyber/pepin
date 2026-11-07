// pepin-line-scan — A4 dogfood application, second program (LUCY-20261107-008 Q3).
// Counts LF bytes (byte value 10) in the granted SourceBytes document,
// i.e. the line-break count of the input file. Returns the count as Int.
// Same predicates, grant path and output contract as pepin-source-scan;
// does NOT modify pepin-source-scan.pep (frozen at 874cc02).
// Shape note: the if has a filled then and an EMPTY ELSE, which A3 proved
// builds (empty_else.pep exit 0); there is no empty-then idiom here.

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
    if byte_at(source, o) == 10 {
      n = n + 1
    } else {
    }
    o = o + 1
  }
  return n
}
