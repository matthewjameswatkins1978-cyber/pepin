# Does byte classification need SourceBytes, or will a Str do? Tokenising any input
# requires per-byte access, so this decides whether a Pep tokeniser can exist at all
# without the host-grant path.
fn main() -> Int {
    let text = "abc"
    let n = byte_length(text)
    return n
}