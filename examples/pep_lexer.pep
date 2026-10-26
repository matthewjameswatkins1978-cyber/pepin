type SourcePosition { line: Int, column: Int }
type Utf8Check { width: Int, invalidOffset: Int }
type LexToken {
  kind: Str,
  text: Str,
  integerValue: Int,
  stringParts: List[Str],
  startByte: Int,
  endByte: Int,
  line: Int,
  column: Int
}
type LexCursor {
  document: Str,
  revision: Str,
  status: Str,
  stage: Str,
  offset: Int,
  line: Int,
  column: Int,
  mode: Str,
  tokenStart: Int,
  tokenLine: Int,
  tokenColumn: Int,
  integerValue: Int,
  integerOverflow: Bool,
  escapePending: Bool,
  stringPartStart: Int,
  stringPartsReversed: List[Str]
}
type LexProgress {
  document: Str,
  revision: Str,
  status: Str,
  tokens: List[LexToken],
  cursor: LexCursor,
  done: Bool,
  errorCode: Str,
  errorStart: Int,
  errorEnd: Int,
  errorLine: Int,
  errorColumn: Int
}

fn ascii_letter(byte: Int) -> Bool {
  return (65 <= byte && byte <= 90) || (97 <= byte && byte <= 122) || byte == 95
}

fn ascii_digit(byte: Int) -> Bool {
  return 48 <= byte && byte <= 57
}

fn ascii_continue(byte: Int) -> Bool {
  return ascii_letter(byte) || ascii_digit(byte)
}

fn utf8_check(source: SourceBytes, offset: Int, length: Int) -> Utf8Check {
  let first = byte_at(source, offset)
  if first <= 127 { return Utf8Check { width: 1, invalidOffset: -1 } } else { }
  var width = 0
  var minimum = 0
  if 192 <= first && first <= 223 { width = 2; minimum = 128 } else { }
  if 224 <= first && first <= 239 { width = 3; minimum = 2048 } else { }
  if 240 <= first && first <= 247 { width = 4; minimum = 65536 } else { }
  if width == 0 { return Utf8Check { width: 0, invalidOffset: offset } } else { }
  if length <= offset + width - 1 { return Utf8Check { width: 0, invalidOffset: offset } } else { }
  var codepoint = 0
  if width == 2 { codepoint = first - 192 } else { }
  if width == 3 { codepoint = first - 224 } else { }
  if width == 4 { codepoint = first - 240 } else { }
  var j = 1
  while !(width <= j) {
    let next = byte_at(source, offset + j)
    if !(128 <= next) || !(next <= 191) {
      return Utf8Check { width: 0, invalidOffset: offset + j }
    } else { }
    codepoint = codepoint * 64 + next - 128
    j = j + 1
  }
  if !(minimum <= codepoint) || !(codepoint <= 1114111) || (55296 <= codepoint && codepoint <= 57343) {
    return Utf8Check { width: 0, invalidOffset: offset }
  } else { }
  if first == 224 && !(160 <= byte_at(source, offset + 1)) { return Utf8Check { width: 0, invalidOffset: offset } } else { }
  if first == 237 && 160 <= byte_at(source, offset + 1) { return Utf8Check { width: 0, invalidOffset: offset } } else { }
  if first == 240 && !(144 <= byte_at(source, offset + 1)) { return Utf8Check { width: 0, invalidOffset: offset } } else { }
  if first == 244 && 144 <= byte_at(source, offset + 1) { return Utf8Check { width: 0, invalidOffset: offset } } else { }
  return Utf8Check { width: width, invalidOffset: -1 }
}

fn advance_position(line: Int, column: Int, byte: Int) -> SourcePosition {
  if byte == 10 { return SourcePosition { line: line + 1, column: 1 } } else {
    return SourcePosition { line: line, column: column + 1 }
  }
}

fn make_cursor(
  document: Str, revision: Str, status: Str, stage: Str,
  offset: Int, line: Int, column: Int, mode: Str,
  tokenStart: Int, tokenLine: Int, tokenColumn: Int,
  integerValue: Int, integerOverflow: Bool, escapePending: Bool,
  stringPartStart: Int, stringPartsReversed: List[Str]
) -> LexCursor {
  return LexCursor {
    document: document, revision: revision, status: status, stage: stage,
    offset: offset, line: line, column: column, mode: mode,
    tokenStart: tokenStart, tokenLine: tokenLine, tokenColumn: tokenColumn,
    integerValue: integerValue, integerOverflow: integerOverflow,
    escapePending: escapePending, stringPartStart: stringPartStart,
    stringPartsReversed: stringPartsReversed
  }
}

fn make_token(
  kind: Str, text: Str, integerValue: Int, stringParts: List[Str],
  startByte: Int, endByte: Int, line: Int, column: Int
) -> LexToken {
  return LexToken {
    kind: kind, text: text, integerValue: integerValue,
    stringParts: stringParts, startByte: startByte, endByte: endByte,
    line: line, column: column
  }
}

fn make_progress(
  document: Str, revision: Str, status: Str, tokens: List[LexToken],
  cursor: LexCursor, done: Bool, errorCode: Str,
  errorStart: Int, errorEnd: Int, errorLine: Int, errorColumn: Int
) -> LexProgress {
  return LexProgress {
    document: document, revision: revision, status: status, tokens: tokens,
    cursor: cursor, done: done, errorCode: errorCode,
    errorStart: errorStart, errorEnd: errorEnd,
    errorLine: errorLine, errorColumn: errorColumn
  }
}

fn lexer_start() -> LexCursor {
  let info = semantic_snapshot()
  return make_cursor(info.document, info.revision, info.status, "validate",
    0, 1, 1, "", 0, 1, 1, 0, false, false, 0, [])
}

fn lexer_step(cursor: LexCursor) -> LexProgress {
  let info = semantic_snapshot()
  if cursor.document != info.document || cursor.revision != info.revision {
    return make_progress(info.document, info.revision, info.status, [], cursor,
      true, "PEP_LEXER_CURSOR_REVISION", 0, 0, 0, 0)
  } else { }
  let source = source_bytes()
  let length = byte_length(source)
  if cursor.offset <= -1 || !(cursor.offset <= length) || cursor.line <= 0 || cursor.column <= 0 {
    return make_progress(info.document, info.revision, info.status, [], cursor,
      true, "PEP_LEXER_CURSOR_RANGE", 0, 0, 0, 0)
  } else { }
  if cursor.mode != "" &&
     (cursor.tokenStart <= -1 || !(cursor.tokenStart <= cursor.offset) ||
      cursor.tokenLine <= 0 || cursor.tokenColumn <= 0) {
    return make_progress(info.document, info.revision, info.status, [], cursor,
      true, "PEP_LEXER_CURSOR_STATE", 0, 0, 0, 0)
  } else { }
  if cursor.mode == "string" &&
     (!(cursor.tokenStart <= cursor.stringPartStart) || !(cursor.stringPartStart <= cursor.offset)) {
    return make_progress(info.document, info.revision, info.status, [], cursor,
      true, "PEP_LEXER_CURSOR_STATE", 0, 0, 0, 0)
  } else { }
  if cursor.stage == "validate" && cursor.mode != "" {
    return make_progress(info.document, info.revision, info.status, [], cursor,
      true, "PEP_LEXER_CURSOR_STATE", 0, 0, 0, 0)
  } else { }
  if cursor.stage == "done" || cursor.stage == "error" {
    return make_progress(info.document, info.revision, info.status, [], cursor,
      true, "", 0, 0, 0, 0)
  } else { }
  if cursor.stage != "validate" && cursor.stage != "scan" {
    return make_progress(info.document, info.revision, info.status, [], cursor,
      true, "PEP_LEXER_CURSOR_STATE", 0, 0, 0, 0)
  } else { }
  if cursor.mode != "" && cursor.mode != "name" && cursor.mode != "number" &&
     cursor.mode != "question" && cursor.mode != "named_hole" &&
     cursor.mode != "string" && cursor.mode != "comment" {
    return make_progress(info.document, info.revision, info.status, [], cursor,
      true, "PEP_LEXER_CURSOR_STATE", 0, 0, 0, 0)
  } else { }

  var stage = cursor.stage
  var offset = cursor.offset
  var line = cursor.line
  var column = cursor.column
  var mode = cursor.mode
  var tokenStart = cursor.tokenStart
  var tokenLine = cursor.tokenLine
  var tokenColumn = cursor.tokenColumn
  var integerValue = cursor.integerValue
  var integerOverflow = cursor.integerOverflow
  var escapePending = cursor.escapePending
  var stringPartStart = cursor.stringPartStart
  var stringPartsReversed = cursor.stringPartsReversed
  var tokens: List[LexToken] = []
  var processed = 0
  var done = false
  var errorCode: Str = ""
  var errorStart = 0
  var errorEnd = 0
  var errorLine = 0
  var errorColumn = 0

  while !(32 <= processed) && !done && errorCode == "" {
    if stage == "validate" {
      if length <= offset {
        stage = "scan"
        offset = 0
        line = 1
        column = 1
        mode = ""
        processed = 32
      } else {
        let check = utf8_check(source, offset, length)
        if check.invalidOffset != -1 {
          var badLine = line
          var badColumn = column
          var bad = offset
          while !(check.invalidOffset <= bad) {
            let position = advance_position(badLine, badColumn, byte_at(source, bad))
            badLine = position.line
            badColumn = position.column
            bad = bad + 1
          }
          errorCode = "PEP_INVALID_UTF8"
          errorStart = check.invalidOffset
          errorEnd = check.invalidOffset + 1
          errorLine = badLine
          errorColumn = badColumn
          done = true
          stage = "error"
        } else {
          var consumed = 0
          while !(check.width <= consumed) {
            let position = advance_position(line, column, byte_at(source, offset))
            line = position.line
            column = position.column
            offset = offset + 1
            processed = processed + 1
            consumed = consumed + 1
          }
        }
      }
    } else {
      if mode == "name" {
        if !(length <= offset) && ascii_continue(byte_at(source, offset)) {
          offset = offset + 1
          column = column + 1
          processed = processed + 1
        } else {
          let word = utf8_slice(source, tokenStart, offset)
          if word == "_" {
            tokens = prepend(tokens, make_token("hole", "", 0, [], tokenStart, offset, tokenLine, tokenColumn))
          } else {
            tokens = prepend(tokens, make_token("identifier", word, 0, [], tokenStart, offset, tokenLine, tokenColumn))
          }
          mode = ""
        }
      } else { if mode == "number" {
        if !(length <= offset) && ascii_digit(byte_at(source, offset)) {
          let digit = byte_at(source, offset) - 48
          if !integerOverflow {
            if !(integerValue <= 922337203685477580) ||
               (integerValue == 922337203685477580 && 8 <= digit) {
              integerOverflow = true
            } else {
              integerValue = integerValue * 10 + digit
            }
          } else { }
          offset = offset + 1
          column = column + 1
          processed = processed + 1
        } else {
          if integerOverflow {
            errorCode = "PEP_INT_LITERAL_RANGE"
            errorStart = tokenStart
            errorEnd = offset
            errorLine = tokenLine
            errorColumn = tokenColumn
            done = true
            stage = "error"
          } else {
            tokens = prepend(tokens, make_token("integer", "", integerValue, [],
              tokenStart, offset, tokenLine, tokenColumn))
            mode = ""
          }
        }
      } else { if mode == "question" {
        if !(length <= offset) && ascii_letter(byte_at(source, offset)) {
          mode = "named_hole"
        } else {
          tokens = prepend(tokens, make_token("hole", "", 0, [], tokenStart,
            tokenStart + 1, tokenLine, tokenColumn))
          mode = ""
        }
      } else { if mode == "named_hole" {
        if !(length <= offset) && ascii_continue(byte_at(source, offset)) {
          offset = offset + 1
          column = column + 1
          processed = processed + 1
        } else {
          tokens = prepend(tokens, make_token("hole", utf8_slice(source, tokenStart + 1, offset),
            0, [], tokenStart, offset, tokenLine, tokenColumn))
          mode = ""
        }
      } else { if mode == "comment" {
        if !(length <= offset) && byte_at(source, offset) != 10 {
          offset = offset + 1
          column = column + 1
          processed = processed + 1
        } else {
          mode = ""
        }
      } else { if mode == "string" {
        if length <= offset {
          errorCode = "PEP_UNTERMINATED_STRING"
          errorStart = tokenStart
          errorEnd = offset
          errorLine = tokenLine
          errorColumn = tokenColumn
          done = true
          stage = "error"
        } else { if escapePending {
          let escaped = byte_at(source, offset)
          if escaped == 110 || escaped == 114 || escaped == 116 || escaped == 48 || escaped == 92 || escaped == 34 {
            if !(offset - 1 <= stringPartStart) {
              stringPartsReversed = prepend(stringPartsReversed, utf8_slice(source, stringPartStart, offset - 1))
            } else { }
            if escaped == 110 { stringPartsReversed = prepend(stringPartsReversed, "\n") } else { }
            if escaped == 114 { stringPartsReversed = prepend(stringPartsReversed, "\r") } else { }
            if escaped == 116 { stringPartsReversed = prepend(stringPartsReversed, "\t") } else { }
            if escaped == 48 { stringPartsReversed = prepend(stringPartsReversed, "\0") } else { }
            if escaped == 92 { stringPartsReversed = prepend(stringPartsReversed, "\\") } else { }
            if escaped == 34 { stringPartsReversed = prepend(stringPartsReversed, "\"") } else { }
            offset = offset + 1
            column = column + 1
            processed = processed + 1
            stringPartStart = offset
            escapePending = false
          } else {
            errorCode = "PEP_INVALID_ESCAPE"
            errorStart = tokenStart
            errorEnd = offset + 1
            errorLine = tokenLine
            errorColumn = tokenColumn
            done = true
            stage = "error"
          }
        } else {
          let byte = byte_at(source, offset)
          if byte == 34 {
            if !(offset <= stringPartStart) {
              stringPartsReversed = prepend(stringPartsReversed, utf8_slice(source, stringPartStart, offset))
            } else { }
            offset = offset + 1
            column = column + 1
            processed = processed + 1
            tokens = prepend(tokens, make_token("string", "", 0, reverse(stringPartsReversed),
              tokenStart, offset, tokenLine, tokenColumn))
            mode = ""
            stringPartsReversed = []
          } else { if byte == 10 {
            errorCode = "PEP_NEWLINE_IN_STRING"
            errorStart = tokenStart
            errorEnd = offset + 1
            errorLine = tokenLine
            errorColumn = tokenColumn
            done = true
            stage = "error"
          } else { if byte == 92 {
            offset = offset + 1
            column = column + 1
            processed = processed + 1
            escapePending = true
          } else {
            offset = offset + 1
            column = column + 1
            processed = processed + 1
          } } }
        } }
      } else {
        if length <= offset {
          tokens = prepend(tokens, make_token("eof", "", 0, [], offset, offset, line, column))
          done = true
          stage = "done"
        } else {
          let byte = byte_at(source, offset)
          if byte == 32 || byte == 9 || byte == 13 || byte == 10 {
            let position = advance_position(line, column, byte)
            line = position.line
            column = position.column
            offset = offset + 1
            processed = processed + 1
          } else { if byte == 35 {
            tokenStart = offset
            tokenLine = line
            tokenColumn = column
            mode = "comment"
            offset = offset + 1
            column = column + 1
            processed = processed + 1
          } else { if byte == 47 && !(length <= offset + 1) && byte_at(source, offset + 1) == 47 {
            tokenStart = offset
            tokenLine = line
            tokenColumn = column
            mode = "comment"
            offset = offset + 2
            column = column + 2
            processed = processed + 2
          } else { if ascii_letter(byte) {
            tokenStart = offset
            tokenLine = line
            tokenColumn = column
            mode = "name"
          } else { if ascii_digit(byte) {
            tokenStart = offset
            tokenLine = line
            tokenColumn = column
            integerValue = 0
            integerOverflow = false
            mode = "number"
          } else { if byte == 34 {
            tokenStart = offset
            tokenLine = line
            tokenColumn = column
            mode = "string"
            escapePending = false
            stringPartsReversed = []
            offset = offset + 1
            column = column + 1
            processed = processed + 1
            stringPartStart = offset
          } else { if byte == 63 {
            tokenStart = offset
            tokenLine = line
            tokenColumn = column
            mode = "question"
            offset = offset + 1
            column = column + 1
            processed = processed + 1
          } else {
            var width = 1
            var symbol = ""
            if !(length <= offset + 1) {
              let next = byte_at(source, offset + 1)
              if (byte == 60 && next == 61) || (byte == 61 && (next == 61 || next == 62)) ||
                 (byte == 33 && next == 61) || (byte == 38 && next == 38) ||
                 (byte == 124 && next == 124) || (byte == 45 && next == 62) {
                width = 2
              } else { }
            } else { }
            if width == 2 {
              symbol = utf8_slice(source, offset, offset + 2)
            } else {
              if byte == 40 || byte == 41 || byte == 123 || byte == 125 || byte == 91 || byte == 93 ||
                 byte == 44 || byte == 58 || byte == 59 || byte == 43 || byte == 45 || byte == 42 ||
                 byte == 47 || byte == 61 || byte == 46 || byte == 124 || byte == 38 || byte == 33 {
                symbol = utf8_slice(source, offset, offset + 1)
              } else { }
            }
            if symbol == "" {
              errorCode = "PEP_UNEXPECTED_CHARACTER"
              errorStart = offset
              errorEnd = offset + 1
              errorLine = line
              errorColumn = column
              done = true
              stage = "error"
            } else {
              tokens = prepend(tokens, make_token("symbol", symbol, 0, [], offset,
                offset + width, line, column))
              offset = offset + width
              column = column + width
              processed = processed + width
            }
          } } } } } } }
        }
      } } } } } }
    }
  }

  let finalStage = if errorCode != "" { "error" } else { stage }
  let next = make_cursor(cursor.document, cursor.revision, cursor.status, finalStage,
    offset, line, column, mode, tokenStart, tokenLine, tokenColumn,
    integerValue, integerOverflow, escapePending, stringPartStart, stringPartsReversed)
  return make_progress(info.document, info.revision, info.status, reverse(tokens), next,
    done || errorCode != "", errorCode, errorStart, errorEnd, errorLine, errorColumn)
}
