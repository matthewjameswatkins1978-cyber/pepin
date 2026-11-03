// C initializer text built from source-scanned integers.
//
// This is the first stdlib slice that spans both earlier modules: `stdlib/scan.pep` reads the numbers
// out of a SourceBytes document and `stdlib/text_builder.pep` assembles the declaration. The result
// is real C a compiler accepts, which is why the test compiles and runs it rather than comparing text.
//
// `int_text` is the one fragment whose width Pep cannot know (the seed has no Str length), so this
// module reports parts and a count and deliberately does NOT claim a byte total. A caller that needs
// the width measures the joined text, and the test does exactly that.
//
// The emitted declaration names `int64_t`, so a consumer must include <stdint.h>: a fragment is not a
// translation unit, and the native test states that dependency rather than hiding it in a driver.

type CArrayInit {
  status: Str,
  diagnostic: Str,
  count: Int,
  parts: List[Str]
}

fn c_array_refused(diagnostic: Str, count: Int) -> CArrayInit {
  return CArrayInit { status: "unsupported", diagnostic: diagnostic, count: count, parts: [] }
}

// `static const int64_t <name>[] = { 1, 2, 3, };` -- the trailing comma is valid C and keeps the
// element fragments uniform, which removes a branch and a whole class of off-by-one layout bugs.
fn c_int_array(name: Str, nameBytes: Int, source: SourceBytes) -> CArrayInit {
  let length = byte_length(source)
  var parts: List[Str] = ["static const int64_t ", name, "[] = { "]
  var offset = 0
  var count = 0
  while !(length <= offset) {
    offset = scan_skip_space(source, offset)
    if length <= offset {
      offset = length
    } else {
      let scanned = scan_int_at(source, offset)
      if scanned.status == "ok" {
        parts = append(parts, int_text(scanned.value))
        parts = append(parts, ", ")
        count = count + 1
        offset = scanned.nextOffset
      } else {
        return c_array_refused(scanned.diagnostic, count)
      }
    }
  }
  if count == 0 { return c_array_refused("Pep C array initializer needs at least one integer", 0) } else {}
  parts = append(parts, "};")
  return CArrayInit { status: "ok", diagnostic: "", count: count, parts: parts }
}
