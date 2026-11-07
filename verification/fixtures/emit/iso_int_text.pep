# ISOLATION: a single builtin call in an initialiser, nothing else.
fn main() -> Int {
    let text = int_text(42)
    say(text)
    return 0
}