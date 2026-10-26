# Pep tool protocol v2

Tool protocol v2 extends the schema-v3 JSON Lines session. Protocol v1 remains the default reported by `describe --json` and remains scalar-compatible. Each tool operation declares `toolProtocolVersion`; a registration, validation, activation, listing, and invocation must use a consistent version. Tool names are independently registered per source revision and protocol version.

## Typed values

V2 uses typed JSON objects. The supported boundary types are `Int`, `Bool`, `Str`, `Unit`, `List[T]`, and monomorphic named records whose fields recursively use those types. Tagged unions are not transport types. Record fields must be present exactly once, with exact declared names and order. List items are typed values. Integers are signed 64-bit decimal strings; booleans are JSON booleans, strings are JSON strings, and Unit is null.

Scalar and list shape:

```json
{"type":"Int","value":"42"}
{"type":"List[Point]","value":[{"type":"Point","fields":[{"name":"x","value":{"type":"Int","value":"3"}},{"name":"y","value":{"type":"Int","value":"4"}}]}]}
```

Record values use `{"type":"RecordName","fields":[{"name":"fieldName","value":...}]}`. They are checked against the checker-derived type and declared field order. V1 continues to use only scalar `{type,value}` values.

V2 bounds typed values to nesting depth 16 and 10,000 value nodes. A JSONL input or response line is limited to 1,048,576 UTF-8 bytes. Tool execution remains limited to 100,000 interpreter steps and 128 call depth. Limit failures return structured JSONL errors.

## Compiler semantic snapshot

`semantic_snapshot() -> ProgramInfo` is a compiler-known, zero-argument Pep builtin. It is available only during an explicitly host-authorised v2 tool invocation (or validation vector) with a `semanticTarget`. Calling it from ordinary `run`, or without the host grant, produces a runtime error. Pep code cannot choose a target through ambient access.

The immutable, monomorphic records are:

- `FunctionInfo { id: Int; name: Str; startByte: Int; endByte: Int }`
- `CallEdge { caller: Int; callee: Int }`
- `SemanticDiagnostic { code: Str; message: Str; startByte: Int; endByte: Int }`
- `ProgramInfo { document: Str; revision: Str; status: Str; functions: List[FunctionInfo]; calls: List[CallEdge]; roots: List[Int]; diagnostics: List[SemanticDiagnostic] }`

Function IDs are checker-resolved and local to the target revision. Spans are half-open original UTF-8 byte ranges. The call graph comes from resolved calls in checked function bodies; constructors and builtins are not edges. Roots include resolved top-level function calls plus explicit host-supplied entry functions. There is no public-export inference. Duplicate, unknown, or ambiguous entry names are rejected.

A `semanticTarget` has exactly these fields, in order:

```json
{"document":"doc-2","revision":"sha256:<retained revision>","entryFunctions":["main"]}
```

The session requires that the document was opened in that process and that the exact revision is retained. A retained historical revision may be queried after a later edit; the response identifies the target document and revision. This target revision is separate from the immutable tool source revision returned by tool registration and invocation. Invalid targets return explicit diagnostics; incomplete targets return partial information with `status: "incomplete"`. Neither should be interpreted as a definitive unreachable-function result.

A v2 registration signature and validation vector follow the standard operations, with the protocol version and optional target grant:

```jsonl
{"schemaVersion":3,"toolProtocolVersion":2,"op":"tool_register","tool":"summarize","document":"doc-1","revision":"sha256:<tool revision>","function":"summarize"}
{"schemaVersion":3,"toolProtocolVersion":2,"op":"tool_validate","tool":"summarize","document":"doc-1","revision":"sha256:<tool revision>","testVectors":[{"arguments":[],"expect":{"type":"ProgramInfo","fields":[...]},"semanticTarget":{"document":"doc-2","revision":"sha256:<target revision>","entryFunctions":["main"]}}]}
{"schemaVersion":3,"toolProtocolVersion":2,"op":"tool_activate","tool":"summarize","document":"doc-1","revision":"sha256:<tool revision>"}
{"schemaVersion":3,"toolProtocolVersion":2,"op":"tool_invoke","tool":"summarize","arguments":[],"semanticTarget":{"document":"doc-2","revision":"sha256:<target revision>","entryFunctions":["main"]}}
```

Registration still derives signatures from checked Pep functions, validation executes real vectors through the interpreter, and activation remains explicit. `say` remains forbidden transitively. Tool activation and rollback semantics are unchanged. The local host is trusted, not a security sandbox; these read grants constrain the session API and do not create an OS security boundary.