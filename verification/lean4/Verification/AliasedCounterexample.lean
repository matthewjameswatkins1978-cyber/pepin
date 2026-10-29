/-
  Aliased-backing counterexample — the model in which DEC-001 FAILS.

  Same `PepVal` values as `Verification.ValueCopy`, but handles are
  indices into ONE shared store, copying shares the handle, and editing
  rewrites the shared cell in place (the CoW-forgotten / aliased-
  mutable-backing implementation shape).

  Purpose: prove the ValueCopy theorem is not vacuous. The copy-
  independence statement is REFUTED here by explicit executable
  witnesses (`example`s the kernel must accept), so a model that
  could not express genuine edits or genuine sharing could not pass
  both files at once.

  Status: DRAFT, same BLOCKED_SECURITY build label as `ValueCopy.lean`.
-/
import Verification.ValueCopy

/-- A "handle" is an index into a shared store (no deep copy). -/
abbrev Handle := Nat

/-- Read-back through a handle. -/
def aread (s : List PepVal) (h : Handle) : Option PepVal := idx s h

/-- In-place write: rewrites the shared cell (aliasing write). -/
def awrite (s : List PepVal) (h : Handle) (v : PepVal) : List PepVal :=
  upd s h v

/-- Copy = share the SAME handle (no independent copy made). -/
def acopy (h : Handle) : Handle := h

/-- Counterexample store: one cell holding `1`. -/
def cxStore : List PepVal := [.int 1]

/-- Original handle and its "copy" (same index — shared backing). -/
def cxHandle : Handle := 0
def cxCopy : Handle := acopy cxHandle

/-- In-place edit of the original rewrites the shared cell. -/
def cxStore' : List PepVal := awrite cxStore cxHandle (.int 99)

/-- Before the edit, the copy observes `1`. -/
example : aread cxStore cxCopy = some (.int 1) := rfl

/-- After the in-place edit, the copy observes `99`: the earlier
    logical copy WAS mutated — DEC-001 violated. -/
example : aread cxStore' cxCopy = some (.int 99) := rfl

/-- The copy observation changed across the edit. -/
example : aread cxStore' cxCopy ≠ aread cxStore cxCopy := by decide

/-- Existential form: the DEC-001 copy property does NOT hold under
    aliased backing — there exist a store, a handle-copy, and a write
    after which the copy observes a different value. -/
example : ∃ (s s' : List PepVal) (c : Handle) (v : PepVal),
    aread s c = some (.int 1) ∧ s' = awrite s c v ∧
    aread s' c = some (.int 99) :=
  ⟨cxStore, cxStore', cxCopy, .int 99, rfl, rfl, rfl⟩
