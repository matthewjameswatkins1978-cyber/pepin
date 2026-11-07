# byte_slice(Str) -> then byte_length on the result.
fn main() -> Int {
    let text = "abc"
    let s = byte_slice(text, 0, 1)
    let n = byte_length(s)
    return n
}