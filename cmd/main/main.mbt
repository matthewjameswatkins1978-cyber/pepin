///|
extern "C" fn pep_read_stdin() -> Bytes = "pep_read_stdin"

///|
extern "C" fn pep_stdin_error() -> Int32 = "pep_stdin_error"

///|
extern "C" fn pep_exit(status : Int32) -> Unit = "exit"

///|
fn fail(message : String, status : Int32) -> Unit {
  eprintln(message)
  pep_exit(status)
}

///|
fn main {
  let args = @env.args()
  if args.length() < 2 {
    fail("usage: pep-seed check|emit-c|describe --json [FILE]", 2)
  }
  let command = args[1]
  if command == "describe" {
    println(@compiler.describe_json())
    return
  }
  if args.length() < 3 {
    fail("usage: pep-seed check|emit-c FILE [--json]", 2)
  }
  let file = args[2]
  if command != "check" && command != "emit-c" {
    fail("unknown compiler command", 2)
  }
  let source_bytes = pep_read_stdin()
  let input_error = pep_stdin_error()
  if input_error != 0 {
    fail("could not read source input", 2)
  }
  let source = try @utf8.decode(source_bytes[:]) catch {
    @utf8.Malformed(_) => {
      fail("source input is not valid UTF-8", 2)
      ""
    }
  } noraise {
    text => text
  }

  match @compiler.compile(source, file) {
    Err(error) => {
      if args.contains("--json") {
        println(@compiler.diagnostic_json(error))
      } else {
        eprintln(
          "\{error.file}:\{error.position.line}:\{error.position.column}: error[\{error.code}]: \{error.message}",
        )
      }
      pep_exit(1)
    }
    Ok(c_source) =>
      if command == "emit-c" {
        println(c_source)
      } else if args.contains("--json") {
        println("{\"schemaVersion\":1,\"diagnostics\":[]}")
      } else {
        println("check passed")
      }
  }
}
