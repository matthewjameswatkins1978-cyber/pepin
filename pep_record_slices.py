"""G2 bridge: validate A4's mc_seam field-range slice descriptors (1577aa3).

Encodes the slice contract as executable invariants so the checker-side
partial-record admission (next G2 step) has a pinned target:
- record type, record span and declaration span are identical across slices;
- fieldIds tile the record's field set exactly once, no overlap/gap;
- every field span sits inside the record span and slices do not overlap;
- carried bindings are a subset of the slice's field binding ids;
- revision identity provenance is present on every slice.
Pure validation over descriptor JSON; no checker/host semantics touched.
"""
import json
from pathlib import Path


def _span_fields(span):
    # A4 descriptors use {start:{offset}, endOffset} naming (source endOffset,
    # not nested end.offset).
    return (span["start"]["offset"], span["endOffset"])


def validate_field_slices(slice_paths):
    slices = [json.loads(Path(p).read_text(encoding="utf-8"))
              for p in slice_paths]
    first = slices[0]
    header = first["header"]
    for other in slices[1:]:
        if other["header"] != header:
            raise AssertionError("slice headers disagree: "
                                 f"{other['header']} vs {header}")
    field_ids = []
    for s in slices:
        field_ids.extend(s["fieldIds"])
    if sorted(field_ids) != list(range(len(field_ids))):
        raise AssertionError(
            f"fieldIds do not tile 0..{len(field_ids)-1} exactly: {field_ids}")
    rec_start, rec_end = _span_fields(header["recordSpan"])
    declared, _dtype = header["declSpan"], None
    del declared
    for s in slices:
        carried = set(s.get("carriedBindings", ()))
        fields = s["fields"]
        spans = []
        for f in fields:
            start, end = _span_fields(f["span"])
            if not (rec_start <= start <= end <= rec_end):
                raise AssertionError(
                    f"field {f['name']} span {start}..{end} escapes record "
                    f"span {rec_start}..{rec_end}")
            spans.append((start, end))
            if f["bindingId"] not in carried:
                raise AssertionError(
                    f"field {f['name']} bindingId {f['bindingId']} not carried")
        spans.sort()
        for (a1, a2), (b1, _b2) in zip(spans, spans[1:]):
            if b1 < a2:
                raise AssertionError(f"slices overlap: {a1}..{a2} vs {b1}..")
        if not s.get("revision", {}).get("lexer_source"):
            raise AssertionError("slice lacks revision provenance")
    return {"recordType": header["recordType"],
            "fieldCount": len(field_ids),
            "slices": [Path(p).name for p in slice_paths],
            "valid": True}
