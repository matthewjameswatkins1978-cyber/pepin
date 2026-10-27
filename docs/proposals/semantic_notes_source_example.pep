# PEP-SN-001 DESIGN FIXTURE ONLY.
# Today the OCaml seed treats the #@ lines below as ordinary comments.
# This fixture must not be described as a working semantic-note parser.

# A zero channel count is not useful for the downstream audio engine.
# The original algorithm deliberately did not encode that requirement.
#@ intent: "Audio channel count supplied by the calling application"
#@ verify: channels != 0
#@ prefer: latency
fn channel_count(channels: Int) -> Int {
    return channels
}

say(int_text(channel_count(2)))
