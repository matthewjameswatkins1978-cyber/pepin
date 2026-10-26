# Implementation packet A5: The first living Pep tool extension

A4 added immutable nominal records, recursive tagged unions, checked constructors and field access, exhaustive pattern matching, and typed holes inside match arms. This packet adds the first host-managed tool extension to the in-process OCaml seed. It does not add special Pep syntax, rebuild the compiler, or claim that extensions are sandboxed.

## Objective

An ordinary Pep function can be exported as a local tool, validated, explicitly activated, invoked through a versioned JSON message, changed, revalidated, and hot replaced without restarting the session process. The checker remains the authority for function signatures and the interpreter remains the authority for execution.

## Registration and signature

- Register a tool name against an exported Pep function, its document and exact source revision, its checked parameter and return types, a description, and its activation status.
- Derive the signature from the checked function declaration; clients cannot supply or override it.
- The first milestone exposes only scalar parameters and results: Int, Bool, Str, and Unit. Records and tagged unions remain internal to Pep and do not cross the tool message boundary.
- Keep the registry in memory for the lifetime of the existing session process. Preserve each registered entry's source revision and function identity.
- Use explicit states: Registered, Validated, Active, Rejected, and Superseded. A registered or validated function is not callable.

## Validation and activation

Activation is an explicit request and requires all of the following: complete checked source at the registered revision, a supported scalar signature, host policy approval, real interpreter test vectors, and an activation request. A source containing holes, invalid code, or an unsupported type must never become active. Test vectors use typed inputs and expected results and are executed by the Pep interpreter before activation.

Do not make registration itself imply activation. Return structured, versioned validation and activation results with stable status and diagnostic information.

## Invocation message boundary

- Add versioned JSONL operations for tool registration, validation, activation, listing, and invocation within the existing session protocol.
- Resolve invocation by active tool identity and its immutable revision-bound entry. Validate argument count and types before evaluation.
- Encode Int values as signed 64-bit decimal strings. Encode Bool, Str, and Unit as JSON boolean, string, and null values inside the typed versioned envelope.
- Do not accept raw ASTs, document references, or caller-supplied type declarations as invocation arguments. Do not expose records or variants on this boundary.
- Keep protocol output as valid JSONL; Pep output cannot inject unframed text into the protocol stream.

## Runtime limits and trust boundary

This is a trusted local prototype, not a sandbox. The tool host provides no arbitrary filesystem, network, environment-variable, or process access. Exported computations are pure Pep functions and may call permitted Pep functions. Enforce call-depth and execution-step budgets in the interpreter. Reject say, including direct or transitive calls to say, from exported computations so tool execution cannot write to the session output stream. Document the trust boundary clearly; do not claim isolation from hostile code.

## Hot replacement

A replacement is checked against the active tool's supported external signature. Run its real test vectors before activation. If the replacement is invalid, incomplete, incompatible, or fails validation, reject it and keep the last active revision callable. On success, activate the replacement atomically and mark the prior entry Superseded. Calls resolve to one immutable revision identity; an in-flight call, if supported, must keep that identity for its duration. No concurrency support is required for this milestone.

## Listing and discovery

tool_list returns tool names, parameter and result types, descriptions, active revision, status, and whether the entry is callable. Registered, validated, rejected, and superseded entries are not callable. Only an active compatible entry can be invoked.

## Acceptance

Automate the full scenario through the real session JSONL interface:

1. Open a document containing an ordinary Pep function such as calculate_fee.
2. Inspect its checker-derived scalar signature.
3. Register, validate with real test vectors, and explicitly activate it.
4. List the tool and invoke it with typed JSON arguments; parse every output line as JSON.
5. Edit the function in a new document revision, validate a compatible replacement, activate it, and observe a different invocation result.
6. Attempt an invalid or incompatible replacement and prove the previous active revision remains callable.
7. Verify rejected, incomplete, unsupported-signature, and side-effecting functions never become callable.
8. Verify argument count/type errors, call-depth and step limits, and direct plus transitive say rejection.

## A5 implementation status

A5 passed its acceptance gate on 2026-10-26. The full repository suite passed 56 tests: 45 OCaml CLI tests and 11 historical MoonBit tests. Real session JSONL tests cover registration, checker-derived signatures, scalar values, test-vector validation, explicit activation, invocation, hot replacement, failed replacement preservation, incomplete and unsupported functions, direct and transitive say rejection, argument errors, call-depth limits, and execution-step limits. The registry is process-local and trusted; it is not a sandbox. No later implementation packet is specified here.

The A5 acceptance gate required complete OCaml and historical MoonBit suites and focused real-session JSONL checks. See [SESSION_PROTOCOL.md](SESSION_PROTOCOL.md) for the implemented request boundary and runtime limits.