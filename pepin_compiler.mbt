///|
pub(all) struct Position {
  line : Int32
  column : Int32
}

///|
pub(all) struct Diagnostic {
  code : String
  message : String
  file : String
  position : Position
}

///|
priv enum TokenKind {
  Identifier(String)
  StringLiteral(String)
  LeftParen
  RightParen
  Semicolon
  End
}

///|
priv struct Token {
  kind : TokenKind
  position : Position
}

///|
priv struct Statement {
  position : Position
  value : String
}

///|
priv struct DiagnosticRecord {
  code : String
  severity : String
  message : String
  file : String
  line : Int32
  column : Int32
} derive(@json.ToJson)

///|
priv struct DiagnosticDocument {
  schemaVersion : Int32
  diagnostics : Array[DiagnosticRecord]
} derive(@json.ToJson)

///|
priv struct DescribeDocument {
  schemaVersion : Int32
  language : String
  languageVersion : String
  implemented : Array[String]
} derive(@json.ToJson)

///|
fn diagnostic(
  code : String,
  message : String,
  file : String,
  position : Position,
) -> Diagnostic {
  { code, message, file, position, }
}

///|
fn is_space(ch : Char) -> Bool {
  ch == ' ' || ch == '\t' || ch == '\r' || ch == '\n'
}

///|
fn is_identifier_start(ch : Char) -> Bool {
  (ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') || ch == '_'
}

///|
fn is_identifier_continue(ch : Char) -> Bool {
  is_identifier_start(ch) || (ch >= '0' && ch <= '9')
}

///|
fn lex(source : String, file : String) -> Result[Array[Token], Diagnostic] {
  let chars = source.to_array()
  let tokens : Array[Token] = []
  let mut i = 0
  let mut line = 1
  let mut column = 1
  while i < chars.length() {
    let ch = chars[i]
    if is_space(ch) {
      if ch == '\r' {
        if i + 1 < chars.length() && chars[i + 1] == '\n' {
          i = i + 1
        }
        line = line + 1
        column = 1
      } else if ch == '\n' {
        line = line + 1
        column = 1
      } else {
        column = column + 1
      }
      i = i + 1
      continue
    }
    let position = { line, column, }
    if is_identifier_start(ch) {
      let start = i
      while i < chars.length() && is_identifier_continue(chars[i]) {
        i = i + 1
        column = column + 1
      }
      tokens.push({
        kind: Identifier(String::from_array(chars[start:i])),
        position,
      })
      continue
    }
    if ch == '"' {
      i = i + 1
      column = column + 1
      let value = StringBuilder()
      let mut closed = false
      while i < chars.length() && !closed {
        let current = chars[i]
        if current == '"' {
          closed = true
          i = i + 1
          column = column + 1
        } else if current == '\r' || current == '\n' {
          return Err(
            diagnostic(
              "LEX002", "String literals cannot contain a raw line break", file,
              position,
            ),
          )
        } else if current.to_int() == 92 {
          i = i + 1
          column = column + 1
          if i >= chars.length() {
            return Err(
              diagnostic(
                "LEX002", "Unterminated string literal", file, position,
              ),
            )
          }
          let escaped = chars[i]
          if escaped == 'n' {
            value.write_char('\n')
          } else if escaped == 'r' {
            value.write_char('\r')
          } else if escaped == 't' {
            value.write_char('\t')
          } else if escaped == '0' {
            value.write_char('\u{0}')
          } else if escaped.to_int() == 92 || escaped == '"' {
            value.write_char(escaped)
          } else {
            return Err(
              diagnostic("LEX003", "Unsupported string escape", file, {
                line,
                column,
              }),
            )
          }
          i = i + 1
          column = column + 1
        } else {
          value.write_char(current)
          i = i + 1
          column = column + 1
        }
      }
      if !closed {
        return Err(
          diagnostic("LEX002", "Unterminated string literal", file, position),
        )
      }
      tokens.push({ kind: StringLiteral(value.to_string()), position, })
      continue
    }
    if ch == '(' {
      tokens.push({ kind: LeftParen, position, })
    } else if ch == ')' {
      tokens.push({ kind: RightParen, position, })
    } else if ch == ';' {
      tokens.push({ kind: Semicolon, position, })
    } else {
      return Err(
        diagnostic("LEX001", "Unexpected character in source", file, position),
      )
    }
    i = i + 1
    column = column + 1
  }
  tokens.push({ kind: End, position: { line, column, }, })
  Ok(tokens)
}

///|
fn parse(
  tokens : Array[Token],
  file : String,
) -> Result[Array[Statement], Diagnostic] {
  let statements : Array[Statement] = []
  let mut i = 0
  while i < tokens.length() && !(tokens[i].kind is End) {
    let token = tokens[i]
    match token.kind {
      Identifier(name) => {
        if name != "say" {
          return Err(
            diagnostic(
              "SEM001",
              "Unsupported construct: only the say builtin is available",
              file,
              token.position,
            ),
          )
        }
        i = i + 1
        if i >= tokens.length() || !(tokens[i].kind is LeftParen) {
          return Err(
            diagnostic(
              "PARSE001",
              "Expected '(' after say",
              file,
              token.position,
            ),
          )
        }
        i = i + 1
        if i >= tokens.length() {
          return Err(
            diagnostic(
              "PARSE001",
              "Expected a string literal inside say(...) ",
              file,
              token.position,
            ),
          )
        }
        let value = match tokens[i].kind {
          StringLiteral(text) => text
          _ =>
            return Err(
              diagnostic(
                "PARSE001",
                "Expected a string literal inside say(...) ",
                file,
                tokens[i].position,
              ),
            )
        }
        i = i + 1
        if i >= tokens.length() || !(tokens[i].kind is RightParen) {
          return Err(
            diagnostic(
              "PARSE001",
              "Expected ')' after the say argument",
              file,
              tokens[i - 1].position,
            ),
          )
        }
        i = i + 1
        statements.push({ position: token.position, value, })
        if i < tokens.length() && tokens[i].kind is Semicolon {
          i = i + 1
        }
      }
      _ =>
        return Err(
          diagnostic(
            "PARSE001",
            "Expected a statement beginning with say",
            file,
            token.position,
          ),
        )
    }
  }
  Ok(statements)
}

///|
fn generate_c(statements : Array[Statement]) -> String {
  let output = StringBuilder()
  output.write_string("#include \"pep_runtime.h\"\n\nint main(void) {\n")
  for statement in statements {
    output.write_string("  /* source at line ")
    output.write_string(statement.position.line.to_string())
    output.write_string(":")
    output.write_string(statement.position.column.to_string())
    output.write_string(" */\n")
    let bytes = @utf8.encode(statement.value)
    output.write_string("  pep_say((const unsigned char[]){")
    if bytes.length() == 0 {
      output.write_string("0")
    } else {
      for index in 0..<bytes.length() {
        if index > 0 {
          output.write_string(", ")
        }
        output.write_string(bytes[index].to_int().to_string())
      }
    }
    output.write_string("}, ")
    output.write_string(bytes.length().to_string())
    output.write_string(");\n")
  }
  output.write_string("  return 0;\n}\n")
  output.to_string()
}

///|
pub fn compile(source : String, file : String) -> Result[String, Diagnostic] {
  match lex(source, file) {
    Err(error) => Err(error)
    Ok(tokens) =>
      match parse(tokens, file) {
        Err(error) => Err(error)
        Ok(statements) => Ok(generate_c(statements))
      }
  }
}

///|
pub fn diagnostic_json(error : Diagnostic) -> String {
  @json.to_json(DiagnosticDocument::{
    schemaVersion: 1,
    diagnostics: [
      DiagnosticRecord::{
        code: error.code,
        severity: "error",
        message: error.message,
        file: error.file,
        line: error.position.line,
        column: error.position.column,
      },
    ],
  }).stringify()
}

///|
pub fn describe_json() -> String {
  @json.to_json(DescribeDocument::{
    schemaVersion: 1,
    language: "Pep",
    languageVersion: "0.2",
    implemented: [
      "string_literals", "say_builtin", "C11_backend", "json_diagnostics",
    ],
  }).stringify()
}
