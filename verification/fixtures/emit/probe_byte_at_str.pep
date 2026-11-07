# Is the Str rejection specific to byte_length, or general to the byte builtins?
fn main() -> Int {
    let text = "abc"
    let b = byte_at(text, 0)
    return b
}