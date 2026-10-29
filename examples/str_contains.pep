# Exact UTF-8 substring search; no Unicode normalization.
# Str is valid UTF-8 text. Empty needles match, and embedded U+0000 is supported.
say(int_text(if str_contains("café au lait", "é au") { 1 } else { 0 }))
say(int_text(if str_contains("cat", "") { 1 } else { 0 }))
say(int_text(if str_contains("", "") { 1 } else { 0 }))
say(int_text(if str_contains("a\0b", "\0") { 1 } else { 0 }))
say(int_text(if str_contains("café", "é") { 1 } else { 0 }))
