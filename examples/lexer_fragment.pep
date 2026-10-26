type LexToken { kind: Str, startByte: Int, endByte: Int, line: Int, column: Int, lexeme: Str }
type LexReport { document: Str, revision: Str, status: Str, tokens: List[LexToken], errorCode: Str, errorStart: Int, errorEnd: Int, errorLine: Int, errorColumn: Int }

fn ascii_letter(byte: Int) -> Bool {
  return (byte <= 90 && !(byte <= 64)) || (byte <= 122 && !(byte <= 96)) || byte == 95
}

fn ascii_digit(byte: Int) -> Bool {
  return byte <= 57 && !(byte <= 47)
}

fn ascii_continue(byte: Int) -> Bool {
  return ascii_letter(byte) || ascii_digit(byte)
}

type SourcePosition { line: Int, column: Int }

fn byte_position(source: Str, target: Int) -> SourcePosition {
  var i = 0
  var line = 1
  var column = 1
  while !(target <= i) {
    if byte_at(source, i) == 10 { line = line + 1; column = 1 } else { column = column + 1 }
    i = i + 1
  }
  return SourcePosition { line: line, column: column }
}

fn utf8_error(source: Str) -> Int {
  var i = 0
  let length = byte_length(source)
  while !(length <= i) {
    let first = byte_at(source, i)
    if first <= 127 {
      i = i + 1
    } else {
      var width = 0
      var secondMinimum = 128
      var secondMaximum = 191
      if !(first <= 193) && first <= 223 { width = 2 } else { }
      if first == 224 { width = 3; secondMinimum = 160 } else { }
      if first <= 236 && !(first <= 224) { width = 3 } else { }
      if first == 237 { width = 3; secondMaximum = 159 } else { }
      if first <= 239 && !(first <= 237) { width = 3 } else { }
      if first == 240 { width = 4; secondMinimum = 144 } else { }
      if first <= 243 && !(first <= 240) { width = 4 } else { }
      if first == 244 { width = 4; secondMaximum = 143 } else { }
      if width == 0 { return i } else {
        if length <= i + width - 1 { return i } else {
          var j = 1
          while !(width <= j) {
            let continuation = byte_at(source, i + j)
            var minimum = 128
            var maximum = 191
            if j == 1 { minimum = secondMinimum; maximum = secondMaximum } else { }
            if continuation <= minimum - 1 || maximum <= continuation - 1 { if j == 1 && (minimum != 128 || maximum != 191) { return i } else { return i + j } } else { j = j + 1 }
          }
          i = i + width
        }
      }
    }
  }
  return -1
}
fn make_token(source: Str, kind: Str, start: Int, finish: Int, line: Int, column: Int) -> LexToken {
  return LexToken { kind: kind, startByte: start, endByte: finish, line: line, column: column, lexeme: byte_slice(source, start, finish) }
}

fn make_report(info: ProgramInfo, tokens: List[LexToken], code: Str, start: Int, finish: Int, line: Int, column: Int) -> LexReport {
  return LexReport { document: info.document, revision: info.revision, status: info.status, tokens: tokens, errorCode: code, errorStart: start, errorEnd: finish, errorLine: line, errorColumn: column }
}

fn lex_fragment() -> LexReport {
  let info = semantic_snapshot()
  let source = source_bytes()
  var tokens: List[LexToken] = []
  var errorCode: Str = ""
  var errorStart = 0
  var errorEnd = 0
  var errorLine = 1
  var errorColumn = 1
  let invalidOffset = utf8_error(source)
  if invalidOffset != -1 {
    let position = byte_position(source, invalidOffset)
    return make_report(info, tokens, "PEP_INVALID_UTF8", invalidOffset, invalidOffset + 1, position.line, position.column)
  } else { }
  var i = 0
  var line = 1
  var column = 1
  let length = byte_length(source)
  while !(length <= i) {
    let byte = byte_at(source, i)
    if byte == 32 || byte == 9 || byte == 13 || byte == 10 {
      if byte == 10 { line = line + 1; column = 1 } else { column = column + 1 }
      i = i + 1
    } else { if byte == 35 || (byte == 47 && !(length <= i + 1) && byte_at(source, i + 1) == 47) {
      while !(length <= i) && byte_at(source, i) != 10 {
        i = i + 1
        column = column + 1
      }
    } else { if ascii_letter(byte) {
      let start = i
      let startColumn = column
      while !(length <= i) && ascii_continue(byte_at(source, i)) {
        i = i + 1
        column = column + 1
      }
      tokens = prepend(tokens, make_token(source, "name", start, i, line, startColumn))
    } else { if ascii_digit(byte) {
      let start = i
      let startColumn = column
      while !(length <= i) && ascii_digit(byte_at(source, i)) {
        i = i + 1
        column = column + 1
      }
      tokens = prepend(tokens, make_token(source, "number", start, i, line, startColumn))
    } else { if byte == 34 {
      let start = i
      let startColumn = column
      var closed = false
      errorCode = ""
      i = i + 1
      column = column + 1
      while !(length <= i) && !closed && errorCode == "" {
        let current = byte_at(source, i)
        if current == 34 {
          i = i + 1
          column = column + 1
          closed = true
        } else { if current == 10 {
          errorCode = "PEP_NEWLINE_IN_STRING"
          errorStart = start
          errorEnd = i + 1
          errorLine = line
          errorColumn = startColumn
        } else { if current == 92 {
          if length <= i + 1 {
            errorCode = "PEP_UNTERMINATED_STRING"
            errorStart = start
            errorEnd = i + 1
            errorLine = line
            errorColumn = startColumn
          } else {
            let escaped = byte_at(source, i + 1)
            if escaped == 110 || escaped == 114 || escaped == 116 || escaped == 48 || escaped == 92 || escaped == 34 {
              i = i + 2
              column = column + 2
            } else {
              errorCode = "PEP_INVALID_ESCAPE"
              errorStart = i
              errorEnd = i + 2
              errorLine = line
              errorColumn = column
            }
          }
        } else {
          i = i + 1
          column = column + 1
        }
      }
        }
      }
      if errorCode != "" { return make_report(info, reverse(tokens), errorCode, errorStart, errorEnd, errorLine, errorColumn) } else { }
      if !closed { return make_report(info, reverse(tokens), "PEP_UNTERMINATED_STRING", start, length, line, startColumn) } else { }
      tokens = prepend(tokens, make_token(source, "string", start, i, line, startColumn))
    } else {
      let start = i
      let startColumn = column
      var width = 1
      if !(length <= i + 1) {
        let next = byte_at(source, i + 1)
        if (byte == 60 && next == 61) || (byte == 61 && (next == 61 || next == 62)) || (byte == 33 && next == 61) || (byte == 38 && next == 38) || (byte == 124 && next == 124) || (byte == 45 && next == 62) { width = 2 } else { }
      } else { }
      if byte == 40 || byte == 41 || byte == 123 || byte == 125 || byte == 91 || byte == 93 || byte == 44 || byte == 58 || byte == 59 || byte == 43 || byte == 45 || byte == 42 || byte == 47 || byte == 61 || byte == 46 || byte == 33 || byte == 38 || byte == 124 || byte == 63 || (byte == 60 && width == 2) {
        i = i + width
        column = column + width
        tokens = prepend(tokens, make_token(source, "symbol", start, i, line, startColumn))
      } else {
        return make_report(info, reverse(tokens), "PEP_UNEXPECTED_CHARACTER", start, start + 1, line, startColumn)
      }
    }
      }
    }
  }
}
}
  tokens = prepend(tokens, make_token(source, "eof", length, length, line, column))
  return make_report(info, reverse(tokens), "", 0, 0, 0, 0)
}