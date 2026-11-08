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

fn make_cursor(
  document: Str, revision: Str, status: Str, stage: Str,
  offset: Int, line: Int, column: Int, mode: Str,
  tokenStart: Int, tokenLine: Int, tokenColumn: Int,
  integerValue: Int, integerOverflow: Bool, escapePending: Bool,
  stringPartStart: Int, stringPartsReversed: List[Str]
) -> LexCursor {
  return LexCursor {
    document: document, revision: revision, status: status, stage: stage,
    offset: "oops", line: line, column: column, mode: mode,
    tokenStart: tokenStart, tokenLine: tokenLine, tokenColumn: tokenColumn,
    integerValue: integerValue, integerOverflow: integerOverflow,
    escapePending: escapePending, stringPartStart: stringPartStart,
    stringPartsReversed: stringPartsReversed
  }
}

let parts: List[Str] = []
let c = make_cursor("d", "r", "s", "st", 0, 1, 1, "m", 0, 1, 1, 0, false, false, 0, parts)
say(int_text(c.offset + c.line + c.column))
