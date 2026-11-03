// Byte-level integer scanning over SourceBytes: the first thing every Pep-written lexer needs.
//
// `examples/pep_lexer.pep` hand-rolls digit classification and decimal accumulation inside its own
// cursor. This module is the reusable form: a caller gets a value and the offset after it, or a
// refusal with a diagnostic, and never has to re-derive either.
//
// Boundaries are explicit because the failure modes are real: a lone `byte_at` past the end raises
// PEP_RUNTIME_BYTE_RANGE, and a long digit run silently overflows Int64. Both are refused here with
// a diagnostic rather than left to the caller or to the runtime.

type ScanInt {
  status: Str,
  diagnostic: Str,
  value: Int,
  nextOffset: Int
}

type ScanSum {
  status: Str,
  diagnostic: Str,
  count: Int,
  total: Int
}

fn scan_is_digit(byte: Int) -> Bool {
  return 48 <= byte && byte <= 57
}

fn scan_is_space(byte: Int) -> Bool {
  return byte == 32 || byte == 9 || byte == 10 || byte == 13
}

// Advance past spaces, tabs, CR and LF. Never reads past the end.
fn scan_skip_space(source: SourceBytes, offset: Int) -> Int {
  let length = byte_length(source)
  // A position, not a verdict: a negative offset clamps to the start instead of asking byte_at for a
  // negative index, which would raise PEP_RUNTIME_BYTE_RANGE. The scanners themselves refuse it.
  if !(0 <= offset) { return 0 } else {}
  var current = offset
  while !(length <= current) && scan_is_space(byte_at(source, current)) {
    current = current + 1
  }
  return current
}

// The largest value that can be multiplied by ten and still accept one more digit.
fn scan_max_before_digit() -> Int {
  return 922337203685477580
}

fn scan_refused(diagnostic: Str, offset: Int) -> ScanInt {
  return ScanInt { status: "unsupported", diagnostic: diagnostic, value: 0, nextOffset: offset }
}

// Scan one base-10 integer starting exactly at `offset`. A non-digit refuses instead of returning
// zero, so a caller cannot mistake "nothing here" for "the value 0".
fn scan_int_at(source: SourceBytes, offset: Int) -> ScanInt {
  let length = byte_length(source)
  if !(0 <= offset) { return scan_refused("Pep scan offset is negative", offset) } else {}
  if !(offset <= length) { return scan_refused("Pep scan offset is past the end of the source", offset) } else {}
  if length <= offset { return scan_refused("Pep scan found no digits at the end of the source", offset) } else {}
  if !scan_is_digit(byte_at(source, offset)) { return scan_refused("Pep scan found a non-digit where an integer was required", offset) } else {}
  var value = 0
  var current = offset
  var digits = 0
  while !(length <= current) && scan_is_digit(byte_at(source, current)) {
    let digit = byte_at(source, current) - 48
    // Guarding the MULTIPLY would reject Int64 max itself: 922337203685477580 * 10 still fits, and
    // only the final digit decides whether the result does. So the last digit is what is bounded.
    if scan_max_before_digit() <= value {
      if scan_max_before_digit() == value {
        // At exactly 922337203685477580 only a final digit of 7 or less keeps the result in range.
        if 8 <= digit {
          return scan_refused("Pep scan integer is too large for Int", current)
        } else {}
      } else {
        // Any value already above that threshold overflowed on the next multiply, whatever the digit.
        return scan_refused("Pep scan integer is too large for Int", current)
      }
    } else {}
    value = value * 10 + digit
    digits = digits + 1
    current = current + 1
  }
  return ScanInt { status: "ok", diagnostic: "", value: value, nextOffset: current }
}

// Skip leading space and scan the integer that follows.
fn scan_int_after_space(source: SourceBytes, offset: Int) -> ScanInt {
  return scan_int_at(source, scan_skip_space(source, offset))
}

// Consumer-shaped entry: add up every whitespace-separated integer in the source. This is the shape a
// lexer or a literal-table builder needs, and it exercises skipping, repeated scanning and refusal
// propagation in one pass.
fn scan_int_sum(source: SourceBytes) -> ScanSum {
  let length = byte_length(source)
  var offset = 0
  var count = 0
  var total = 0
  while !(length <= offset) {
    offset = scan_skip_space(source, offset)
    if length <= offset {
      // Trailing whitespace: nothing left to scan; assigning here also ends the pass.
      offset = length
    } else {
      let scanned = scan_int_at(source, offset)
      if scanned.status == "ok" {
        count = count + 1
        total = total + scanned.value
        offset = scanned.nextOffset
      } else {
        return ScanSum { status: "unsupported", diagnostic: scanned.diagnostic, count: count, total: total }
      }
    }
  }
  return ScanSum { status: "ok", diagnostic: "", count: count, total: total }
}

// Identifier scanning, the companion to digit scanning: a lexer needs both and should not re-roll
// either. The slice is taken with `utf8_slice`, so a multi-byte identifier body is returned intact
// and the reported width is bytes, not characters.
fn scan_is_ident_start(byte: Int) -> Bool {
  return (65 <= byte && byte <= 90) || (97 <= byte && byte <= 122) || byte == 95
}

fn scan_is_ident_continue(byte: Int) -> Bool {
  return scan_is_ident_start(byte) || scan_is_digit(byte)
}

type ScanIdent {
  status: Str,
  diagnostic: Str,
  text: Str,
  byteLength: Int,
  nextOffset: Int
}

fn scan_ident_at(source: SourceBytes, offset: Int) -> ScanIdent {
  let length = byte_length(source)
  if !(0 <= offset) {
    return ScanIdent { status: "unsupported", diagnostic: "Pep scan offset is negative", text: "", byteLength: 0, nextOffset: offset }
  } else {}
  if !(offset <= length) {
    return ScanIdent { status: "unsupported", diagnostic: "Pep scan offset is past the end of the source", text: "", byteLength: 0, nextOffset: offset }
  } else {}
  if length <= offset {
    return ScanIdent { status: "unsupported", diagnostic: "Pep scan found no identifier at the end of the source", text: "", byteLength: 0, nextOffset: offset }
  } else {}
  if !scan_is_ident_start(byte_at(source, offset)) {
    return ScanIdent { status: "unsupported", diagnostic: "Pep scan found a non-identifier start byte", text: "", byteLength: 0, nextOffset: offset }
  } else {}
  var current = offset
  while !(length <= current) && scan_is_ident_continue(byte_at(source, current)) {
    current = current + 1
  }
  return ScanIdent {
    status: "ok",
    diagnostic: "",
    text: utf8_slice(source, offset, current),
    byteLength: current - offset,
    nextOffset: current
  }
}

// Consumer-shaped entry: count whitespace-separated identifiers, refusing on anything that is neither
// whitespace nor a valid identifier start. A lexer built on this reports a precise offset instead of
// skipping silently.
type ScanCount {
  status: Str,
  diagnostic: Str,
  count: Int,
  offset: Int
}

// Quoted-literal scanning: the third input a lexer needs beside identifiers and integers.
//
// `examples/pep_lexer.pep` tracks `escapePending` and `stringPartsReversed` by hand inside its cursor.
// This is the reusable form: it returns the decoded fragments and the offset after the closing quote,
// or a refusal that names the byte that stopped it. Fragments are returned rather than one joined
// `Str` because the seed cannot concatenate strings; the caller joins.
//
// Scope, stated rather than implied: single-line literals only (an unescaped newline refuses), escapes
// are \n \t \r \\ and \" only, and \0 is refused because a NUL cannot be written as a Pep literal. An
// unknown escape refuses instead of being passed through, so a caller never silently loses a backslash.

// `isNul` exists because the language accepts `\0` (verified against the OCaml seed: a program with
// `say("a\0b")` runs and emits the NUL) but Pep source has no way to WRITE a NUL character, so a
// fragment cannot carry one. The escape is therefore accepted, contributes no fragment, and is
// counted so a caller can materialise the byte itself instead of the scanner silently dropping it.
type ScanEscape {
  supported: Bool,
  isNul: Bool,
  text: Str
}

fn scan_escape_text(byte: Int) -> ScanEscape {
  if byte == 110 { return ScanEscape { supported: true, isNul: false, text: "\n" } } else {}
  if byte == 116 { return ScanEscape { supported: true, isNul: false, text: "\t" } } else {}
  if byte == 114 { return ScanEscape { supported: true, isNul: false, text: "\r" } } else {}
  if byte == 92 { return ScanEscape { supported: true, isNul: false, text: "\\" } } else {}
  if byte == 34 { return ScanEscape { supported: true, isNul: false, text: "\"" } } else {}
  if byte == 48 { return ScanEscape { supported: true, isNul: true, text: "" } } else {}
  return ScanEscape { supported: false, isNul: false, text: "" }
}

type ScanString {
  status: Str,
  diagnostic: Str,
  parts: List[Str],
  byteLength: Int,
  nextOffset: Int,
  nulCount: Int
}

fn scan_string_refused(diagnostic: Str, offset: Int) -> ScanString {
  return ScanString {
    status: "unsupported",
    diagnostic: diagnostic,
    parts: [],
    byteLength: 0,
    nextOffset: offset,
    nulCount: 0
  }
}

fn scan_string_at(source: SourceBytes, offset: Int) -> ScanString {
  let length = byte_length(source)
  if !(0 <= offset) { return scan_string_refused("Pep scan offset is negative", offset) } else {}
  if !(offset <= length) {
    return scan_string_refused("Pep scan offset is past the end of the source", offset)
  } else {}
  if length <= offset {
    return scan_string_refused("Pep scan found no string literal at the end of the source", offset)
  } else {}
  if !(byte_at(source, offset) == 34) {
    return scan_string_refused("Pep scan found no quote where a string literal was required", offset)
  } else {}
  var parts: List[Str] = []
  var nuls = 0
  var current = offset + 1
  var runStart = current
  while !(length <= current) {
    let byte = byte_at(source, current)
    if byte == 34 {
      if runStart == current {
        // Nothing pending; the literal closed exactly on a run boundary.
      } else {
        parts = append(parts, utf8_slice(source, runStart, current))
      }
      return ScanString {
        status: "ok",
        diagnostic: "",
        parts: parts,
        byteLength: current + 1 - offset,
        nextOffset: current + 1,
        nulCount: nuls
      }
    } else {}
    if byte == 10 {
      return scan_string_refused("Pep scan found an unterminated string literal", offset)
    } else {}
    if byte == 92 {
      if runStart == current {
        // Escape immediately after the opening quote or a previous escape.
      } else {
        parts = append(parts, utf8_slice(source, runStart, current))
      }
      if length <= current + 1 {
        return scan_string_refused("Pep scan found an unterminated escape sequence", current)
      } else {}
      let escape = scan_escape_text(byte_at(source, current + 1))
      if !escape.supported {
        return scan_string_refused("Pep scan found an unsupported string escape", current)
      } else {}
      if escape.isNul {
        // Accepted like the canonical lexer, but a NUL cannot be a Pep Str fragment; count it.
        nuls = nuls + 1
      } else {
        parts = append(parts, escape.text)
      }
      current = current + 2
      runStart = current
    } else {
      current = current + 1
    }
  }
  return scan_string_refused("Pep scan found an unterminated string literal", offset)
}

fn scan_ident_count(source: SourceBytes) -> ScanCount {
  let length = byte_length(source)
  var offset = 0
  var count = 0
  while !(length <= offset) {
    offset = scan_skip_space(source, offset)
    if length <= offset {
      offset = length
    } else {
      let scanned = scan_ident_at(source, offset)
      if scanned.status == "ok" {
        count = count + 1
        offset = scanned.nextOffset
      } else {
        return ScanCount { status: "unsupported", diagnostic: scanned.diagnostic, count: count, offset: offset }
      }
    }
  }
  return ScanCount { status: "ok", diagnostic: "", count: count, offset: offset }
}

// Symbol (punctuation and operator) scanning: the lexer input class the seed tracks as `Sym`,
// beside whitespace, comments, identifiers, integers, quoted literals and holes.
//
// Grammar authority is the seed lexer in `pep_ocaml.ml`, and its precedence is unusual enough to
// state exactly: the seven two-byte forms `<= == != && || -> =>` are tried first, then exactly
// these single bytes `( ) { } [ ] , : ; + - * / = . | & !`. A lone `<` or `>` is NOT a symbol --
// measured live against the OCaml seed, where `let a = 1 < 2;` fails PEP_UNEXPECTED_CHARACTER at
// the `<` -- which is also why every comparison in this file is written `!(b <= a)`. This scanner
// refuses a lone angle bracket instead of inventing a token the parser does not accept, and `?`
// belongs to the hole scanner, so refusing it here is a boundary statement, not a grammar claim.
//
// "Maximal munch" means the seed's exact precedence, not a general operator table: a pair is
// consumed only when both bytes match one of the seven forms, otherwise exactly one byte is
// consumed or the scan refuses at that byte with `byteLength` 0, so a caller can never mistake a
// refusal for a consumed byte.

type ScanSym {
  status: Str,
  diagnostic: Str,
  text: Str,
  byteLength: Int,
  nextOffset: Int
}

fn scan_sym_refused(diagnostic: Str, offset: Int) -> ScanSym {
  return ScanSym { status: "unsupported", diagnostic: diagnostic, text: "", byteLength: 0, nextOffset: offset }
}

// Name the unexpected character WITHOUT splitting it: ASCII is one byte, a UTF-8 lead byte covers
// the widths below, and anything else (a continuation byte or a truncated final sequence) gets no
// text rather than a one-byte slice that would raise PEP_RUNTIME_BYTE_BOUNDARY.
fn scan_sym_unexpected(source: SourceBytes, offset: Int, head: Int) -> ScanSym {
  var width = 0
  if !(128 <= head) { width = 1 } else {}
  if 192 <= head && head <= 223 { width = 2 } else {}
  if 224 <= head && head <= 239 { width = 3 } else {}
  if 240 <= head && head <= 252 { width = 4 } else {}
  var text = ""
  if !(width <= 0) && width <= byte_length(source) - offset {
    text = utf8_slice(source, offset, offset + width)
  } else {}
  return ScanSym {
    status: "unsupported",
    diagnostic: "Pep scan found an unexpected character",
    text: text,
    byteLength: 0,
    nextOffset: offset
  }
}

fn scan_sym_at(source: SourceBytes, offset: Int) -> ScanSym {
  let length = byte_length(source)
  if !(0 <= offset) { return scan_sym_refused("Pep scan offset is negative", offset) } else {}
  if !(offset <= length) { return scan_sym_refused("Pep scan offset is past the end of the source", offset) } else {}
  if length <= offset { return scan_sym_refused("Pep scan found no symbol at the end of the source", offset) } else {}
  let head = byte_at(source, offset)
  var width = 0
  // The seven two-byte forms, each decided by the pair alone; they cannot overlap on the same
  // bytes, so the seed's relative check order between them is irrelevant.
  if !(length <= offset + 1) {
    let next = byte_at(source, offset + 1)
    if head == 60 && next == 61 { width = 2 } else {}
    if head == 61 && next == 61 { width = 2 } else {}
    if head == 33 && next == 61 { width = 2 } else {}
    if head == 38 && next == 38 { width = 2 } else {}
    if head == 124 && next == 124 { width = 2 } else {}
    if head == 45 && next == 62 { width = 2 } else {}
    if head == 61 && next == 62 { width = 2 } else {}
  } else {}
  if width == 0 {
    // The seed's single-byte list, byte-for-byte: ( ) { } [ ] , : ; + - * / = . | & !
    if head == 40 || head == 41 || head == 123 || head == 125 || head == 91 || head == 93 { width = 1 } else {}
    if head == 44 || head == 58 || head == 59 || head == 43 || head == 45 || head == 42 { width = 1 } else {}
    if head == 47 || head == 61 || head == 46 || head == 124 || head == 38 || head == 33 { width = 1 } else {}
  } else {}
  if width == 0 { return scan_sym_unexpected(source, offset, head) } else {}
  return ScanSym {
    status: "ok",
    diagnostic: "",
    text: utf8_slice(source, offset, offset + width),
    byteLength: width,
    nextOffset: offset + width
  }
}

// Consumer-shaped entry: count whitespace-separated symbols, refusing on the first byte that is
// not one -- the same shape as `scan_ident_count`. A driver built on this reports the precise
// offset where its input stopped being punctuation instead of skipping silently.
type ScanSymCount {
  status: Str,
  diagnostic: Str,
  count: Int,
  offset: Int
}

fn scan_sym_count(source: SourceBytes) -> ScanSymCount {
  let length = byte_length(source)
  var offset = 0
  var count = 0
  while !(length <= offset) {
    offset = scan_skip_space(source, offset)
    if length <= offset {
      offset = length
    } else {
      let scanned = scan_sym_at(source, offset)
      if scanned.status == "ok" {
        count = count + 1
        offset = scanned.nextOffset
      } else {
        return ScanSymCount { status: "unsupported", diagnostic: scanned.diagnostic, count: count, offset: offset }
      }
    }
  }
  return ScanSymCount { status: "ok", diagnostic: "", count: count, offset: offset }
}
