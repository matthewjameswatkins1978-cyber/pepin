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
  if !(offset <= length) { return scan_refused("Pep scan offset is past the end of the source", offset) } else {}
  if length <= offset { return scan_refused("Pep scan found no digits at the end of the source", offset) } else {}
  if !scan_is_digit(byte_at(source, offset)) { return scan_refused("Pep scan found a non-digit where an integer was required", offset) } else {}
  var value = 0
  var current = offset
  var digits = 0
  while !(length <= current) && scan_is_digit(byte_at(source, current)) {
    if scan_max_before_digit() <= value {
      return scan_refused("Pep scan integer is too large for Int", current)
    } else {}
    value = value * 10 + (byte_at(source, current) - 48)
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

type ScanEscape {
  supported: Bool,
  text: Str
}

fn scan_escape_text(byte: Int) -> ScanEscape {
  if byte == 110 { return ScanEscape { supported: true, text: "\n" } } else {}
  if byte == 116 { return ScanEscape { supported: true, text: "\t" } } else {}
  if byte == 114 { return ScanEscape { supported: true, text: "\r" } } else {}
  if byte == 92 { return ScanEscape { supported: true, text: "\\" } } else {}
  if byte == 34 { return ScanEscape { supported: true, text: "\"" } } else {}
  return ScanEscape { supported: false, text: "" }
}

type ScanString {
  status: Str,
  diagnostic: Str,
  parts: List[Str],
  byteLength: Int,
  nextOffset: Int
}

fn scan_string_refused(diagnostic: Str, offset: Int) -> ScanString {
  return ScanString { status: "unsupported", diagnostic: diagnostic, parts: [], byteLength: 0, nextOffset: offset }
}

fn scan_string_at(source: SourceBytes, offset: Int) -> ScanString {
  let length = byte_length(source)
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
        nextOffset: current + 1
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
      parts = append(parts, escape.text)
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
