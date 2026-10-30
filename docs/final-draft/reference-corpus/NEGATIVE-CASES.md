# Pepin reference corpus: deliberately invalid cases

**Status:** candidate rejection requirements. Code is schematic; no current compiler execution claimed. Each specimen is independent and must be evaluated with suitable fixtures/imports. Distinguish static rejection, runtime trap and unresolved policy.

## A. Expression typing and error propagation

**N01 Missing value-producing else — static type error**

~~~pep
fn classify(n: Int) -> Str {
    let label: Str = if n > 0 { "positive" }
    label
}
~~~

Expected: if-without-else is Unit; cannot assign to Str.

**N02 Wrong implicit final value — static type error**

~~~pep
fn answer() -> Int {
    "forty-two"
}
~~~

Expected: final Str does not conform to declared Int.

**N03 try on Option — static type error (Result-only rule)**

~~~pep
fn load() -> Result[Int, DataError] {
    try Some(5)
}
~~~

Expected: try requires Result[T,E], not Option[T].

**N04 try with unrelated errors — static type error**

~~~pep
fn load() -> Result[Int, OuterError] {
    let number = try returns_result_int_inner_error()
    Ok(number)
}
~~~

Expected: InnerError cannot silently become OuterError. Explicit map/match necessary.

**N05 Dropped Result — static error**

~~~pep
fn run() -> Unit {
    risky_operation()
}
~~~

Expected when risky_operation returns Result: unexamined Result must not be silently discarded; require handling or explicit acknowledgement.

**N06 Nonexhaustive union match — static error**

~~~pep
fn unwrap(x: Option[Int]) -> Int {
    match x {
        Some(n) => n
    }
}
~~~

Expected: missing None.

## B. Generic coherence and value semantics

**N07 Duplicate canonical implementation — coherence error**

~~~pep
ability Display { fn show(value: Self) -> Str }
type Book { title: Str }
impl Display for Book { fn show(value: Book) -> Str { value.title } }
impl Display for Book { fn show(value: Book) -> Str { "another" } }
~~~

Expected: at most one canonical implementation for Book + Display. Neither declaration silently wins.

**N08 Third-party implementation of third-party type — coherence error**

~~~pep
// In a package owning neither foreign.Book nor foreign.Display:
impl foreign.Display for foreign.Book {
    fn show(value: foreign.Book) -> Str { "override" }
}
~~~

Expected: orphan implementation rejected. Use explicit typed formatter value.

**N09 Invalid Map key contract — type/capability error**

~~~pep
let scores: Map[Float, Int] = map.empty()
~~~

Expected: plain Float with IEEE NaN semantics is not automatically an eligible equivalence+hash key. A specified canonical key wrapper is needed.

**N10 Overlapping exclusive edits — access conflict**

~~~pep
fn combine(edit a: Int, edit b: Int) -> Unit { }
var count = 1
combine(edit count, edit count)
~~~

Expected: two simultaneous exclusive views of same binding rejected.

## C. Ownership, effects and resources

**N11 Use after take — ownership error**

~~~pep
var buffer = try memory.allocate[Byte](16)
try memory.free(take buffer)
memory.write(edit buffer, 0, 42)
~~~

Expected: use of consumed buffer rejected.

**N12 Double free — ownership error**

~~~pep
var buffer = try memory.allocate[Byte](16)
try memory.free(take buffer)
try memory.free(take buffer)
~~~

Expected: second use of consumed resource rejected.

**N13 Undeclared exported effect — effect error**

~~~pep
pub fn secret_read() -> Result[Str, fs.Error]
    uses none
{
    fs.read_text("private.txt")
}
~~~

Expected: filesystem effect cannot pass a pure ceiling. Even declared uses would not grant host authority.

**N14 Bad static refinement — constraint error**

~~~pep
type Port = Int where self >= 0 && self <= 65535
let port = Port(90000)
~~~

Expected: statically refuted bound. Unknown input requires explicit checked conversion instead.

**N15 Raw access outside danger — restricted-operation error**

~~~pep
fn peek(region: device.MmioRegion, offset: Int) -> Int {
    device.read_volatile(region, offset)
}
~~~

Expected: raw/device operation requires bounded danger and separately established authority.

## D. Structured concurrency

**N16 Unowned task — task-scope error**

~~~pep
fn start() -> Unit {
    spawn expensive_work()
}
~~~

Expected: ordinary spawn outside owning task scope rejected.

**N17 Exclusive edit across suspension — access error**

~~~pep
async fn bad(edit data: Data) -> Unit {
    await fetch()
    mutate(edit data)
}
~~~

Expected under initially strict model: outstanding exclusive edit access is not allowed to cross await. A future suspension-safe ownership proof rule could change the admissible set, but no silent inference.

**N18 Task handle escapes owning scope — task-lifetime error**

~~~pep
fn escape() -> Task[Int, JobError] {
    task {
        spawn compute()
    }
}
~~~

Expected: a lexical task handle cannot escape the scope that must own and join/drain it.

## E. Behavioural edge cases, not necessarily static errors

**R01 Checked arithmetic**: 9223372036854775807 + 1 traps as checked Int overflow, not wraparound.

**R02 Indexing**: list.get(-1) yields None; direct list[-1] is a checked runtime bounds failure if not disproved statically.

**R03 Host permission**: a program with valid uses net.read but without host network grant fails the capability boundary; no hidden permission through use import.

**R04 Two simultaneous failures**: an awaited child fails while a sibling's cleanup fails. Primary outcome and additional observed cleanup failures must both be inspectable. Exact error precedence/shape requires binding specification.

**R05 Cleanup on cancellation**: cancelling a task that launched a GPU/network operation cannot declare resources released before actual safe completion, even if the task has stopped executing Pep code.

**R06 Source identity**: an edit based on an old UTF-8 source hash cannot silently apply to a new revision. Byte offsets and untouched LF/CRLF must be preserved.

## The test harness must report

Fixture ID, phase (lex/parse/check/execute/authority), status (valid/incomplete/invalid/ran/trapped/cancelled), diagnostic code and original byte span, compiler revision, policy/assumption dependencies, and interpreter/native differential evidence where applicable. Never convert a timeout, unknown, or runtime permission denial into a claim of type unsafety or compiler acceptance.
