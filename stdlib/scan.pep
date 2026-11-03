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
