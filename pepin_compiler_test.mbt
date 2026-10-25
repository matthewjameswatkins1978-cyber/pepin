///|
test "hello source produces a runtime call" {
  match @pepin.compile("say(\"Hello, Pep!\")", "hello.pep") {
    Ok(c_source) => assert_true(c_source.contains("pep_say"))
    Err(_) => assert_true(false)
  }
}

///|
test "LF and CRLF produce identical C" {
  let lf = @pepin.compile("say(\"one\")\nsay(\"two\")", "lines.pep")
  let crlf = @pepin.compile("say(\"one\")\r\nsay(\"two\")", "lines.pep")
  match (lf, crlf) {
    (Ok(lf_c), Ok(crlf_c)) => assert_eq(lf_c, crlf_c)
    _ => assert_true(false)
  }
}

///|
test "escaped strings become UTF-8 bytes" {
  match @pepin.compile("say(\"quote: \\\"\")", "escape.pep") {
    Ok(c_source) =>
      assert_true(c_source.contains("113, 117, 111, 116, 101, 58, 32, 34"))
    Err(_) => assert_true(false)
  }
}

///|
test "unsupported constructs return a stable diagnostic" {
  match @pepin.compile("print(\"no\")", "bad.pep") {
    Err(error) => assert_eq(error.code, "SEM001")
    Ok(_) => assert_true(false)
  }
}
