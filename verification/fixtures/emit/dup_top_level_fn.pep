// A3-S3 probe: duplicate top-level function names. A1 added a host-side refusal
// claiming to mirror the seed's PEP_DUPLICATE_FUNCTION. This checks the seed's
// own behaviour, so the mirror claim can be verified rather than trusted.
fn main() -> Int {
  return 1
}

fn main() -> Int {
  return 2
}