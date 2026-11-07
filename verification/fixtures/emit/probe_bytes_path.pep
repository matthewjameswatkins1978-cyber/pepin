# INPUT-SENSITIVE PATH WITHOUT utf8_slice: byte_length and byte_at are emittable
# (1 and 3 by-name sites), source_bytes is not (0 sites). This fixture tests whether
# input bytes can be acquired and reduced to an Int at all.
fn main() -> Int {
    let raw = source_bytes("Pep")
    let n = byte_length(raw)
    let b = byte_at(raw, 0)
    let s = b + n
    return s
}