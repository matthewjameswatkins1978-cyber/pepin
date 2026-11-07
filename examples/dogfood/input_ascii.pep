fn identity(flag: Bool) -> Bool { return flag }
fn negate(flag: Bool) -> Bool { return !flag }
fn main() -> Int { return if identity(negate(false)) { 42 } else { 0 } }
