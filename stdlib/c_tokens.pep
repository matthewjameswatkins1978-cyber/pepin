// A token-stream consumer that uses both scanners in one pass and emits a C table.
//
// This is the slice that proves the two halves of `stdlib/scan.pep` compose: one pass over the
// document classifies each whitespace-separated word as an integer or an identifier, counts both, and
// renders the counts as C that a compiler accepts.
//
// Boundary, stated rather than implied: this is a WORD scanner. It splits on whitespace only and does
// not recognise operators, punctuation or quoting, so it is not a lexer and must not be described as
// one. Anything that is neither whitespace nor a digit-leading nor identifier-leading byte is refused
// with the exact offset that stopped the scan.

type CTokenCounts {
  status: Str,
  diagnostic: Str,
  identifiers: Int,
  integers: Int,
  parts: List[Str]
}

fn c_token_counts(name: Str, nameBytes: Int, source: SourceBytes) -> CTokenCounts {
  let length = byte_length(source)
  var identifiers = 0
  var integers = 0
  var offset = 0
  while !(length <= offset) {
    offset = scan_skip_space(source, offset)
    if length <= offset {
      offset = length
    } else {
      let byte = byte_at(source, offset)
      if scan_is_digit(byte) {
        let scanned = scan_int_at(source, offset)
        if scanned.status == "ok" {
          integers = integers + 1
          offset = scanned.nextOffset
        } else {
          return CTokenCounts { status: "unsupported", diagnostic: scanned.diagnostic, identifiers: identifiers, integers: integers, parts: [] }
        }
      } else {
        let scanned = scan_ident_at(source, offset)
        if scanned.status == "ok" {
          identifiers = identifiers + 1
          offset = scanned.nextOffset
        } else {
          return CTokenCounts { status: "unsupported", diagnostic: scanned.diagnostic, identifiers: identifiers, integers: integers, parts: [] }
        }
      }
    }
  }
  if identifiers == 0 && integers == 0 {
    return CTokenCounts { status: "unsupported", diagnostic: "Pep C token counts need at least one token", identifiers: 0, integers: 0, parts: [] }
  } else {}
  var parts: List[Str] = ["static const int64_t ", name, "[] = { ", int_text(identifiers), ", ", int_text(integers), ", };"]
  return CTokenCounts { status: "ok", diagnostic: "", identifiers: identifiers, integers: integers, parts: parts }
}
