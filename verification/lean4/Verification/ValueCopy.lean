/-
  Pep value-copy model — DEC-001 subset.

  Accepted source: PEP-LANG-FINAL-DRAFT-2026-10-27 §4 — ordinary data
  and collections are independent logical values; editing one copy must
  not mutate an earlier logical copy.

  Scope: `Int` / `Bool` scalars, arbitrarily nested `List` values,
  one checked scalar rewrite at an index path, and a copy-then-edit
  snapshot. This mirrors the seed-observable surface:
  `List[T]` literals, immutable `append` (new list), `var` reassignment
  (rebind, old binding keeps its value) — TESTED on the OCaml seed, see
  verification/adversarial/cases/VALUE_COPY_DEC001.md probes P1–P3.

  Explicit assumptions: statically valid index paths (out-of-bounds is
  `none`, never UB); no FFI/host effects; no concurrency; no raw
  pointers; source-level values, not C23/OCaml representations.

  Status: kernel-checked locally on the (formerly held) Windows host
  with leanprover/lean4:v4.35.0 after the #22 native clearance — see
  verification/receipts/lean4-kernel-check.md for the actual run.
  No `sorry`, `admit`, `axiom`, or `native_decide`.

  Kernel-check amendments (tactics/instances only, statements verbatim):
  - Core Lean has no `DecidableEq` deriving handler for NESTED
    inductives, so `PepVal` carries a hand-written mutual decision
    procedure instead of `deriving DecidableEq`.
  - Bare `set` / `get` in tactic position are ambiguous with
    `MonadStateOf.set` / `MonadState.get`, so tactics fully qualify
    `_root_.set` / `_root_.get`.
-/

/-- Small Pep values: scalars plus nested lists (DEC-005 subset). -/
inductive PepVal where
  | int : Int → PepVal
  | bool : Bool → PepVal
  | list : List PepVal → PepVal
  deriving Repr

/- Hand-written structural decision procedure: core Lean's
   `deriving DecidableEq` has no handler for nested inductives. -/
mutual
  def pepDecEq : (a b : PepVal) → Decidable (a = b)
    | .int x, .int y => if h : x = y then isTrue (by simp [h]) else isFalse (by simp [h])
    | .bool x, .bool y => if h : x = y then isTrue (by simp [h]) else isFalse (by simp [h])
    | .list xs, .list ys =>
      match listDecEq xs ys with
      | isTrue h => isTrue (by simp [h])
      | isFalse h => isFalse (by simp [h])
    | .int _, .bool _ | .int _, .list _ | .bool _, .int _
    | .bool _, .list _ | .list _, .int _ | .list _, .bool _ =>
      isFalse (by simp)
  def listDecEq : (xs ys : List PepVal) → Decidable (xs = ys)
    | [], [] => isTrue rfl
    | x :: xs, y :: ys =>
      match pepDecEq x y, listDecEq xs ys with
      | isTrue hxy, isTrue hxs => isTrue (by simp [hxy, hxs])
      | isFalse hxy, _ => isFalse (by simp [hxy])
      | _, isFalse hxs => isFalse (by simp [hxs])
    | [], _ :: _ => isFalse (by simp)
    | _ :: _, [] => isFalse (by simp)
end

instance : DecidableEq PepVal := pepDecEq

/-- Structural index into a list level (own recursion keeps helper
    lemmas provable by plain structural induction). -/
def idx : List PepVal → Nat → Option PepVal
  | [], _ => none
  | x :: _, 0 => some x
  | _ :: xs, n + 1 => idx xs n

/-- Structural single-position update. Out-of-bounds is a no-op list
    (callers check `idx` first, so this case is unreachable on the
    legal path). -/
def upd : List PepVal → Nat → PepVal → List PepVal
  | [], _, _ => []
  | _ :: xs, 0, x' => x' :: xs
  | x :: xs, n + 1, x' => x :: upd xs n x'

/-- Observable read-back at an index path (`none` = invalid path). -/
def get : PepVal → List Nat → Option PepVal
  | v, [] => some v
  | .list xs, i :: rest =>
    match idx xs i with
    | none => none
    | some x => get x rest
  | _, _ :: _ => none

/-- Checked scalar edit: rewrite the `Int` leaf at a path.
    Returns `none` unless the full path exists and ends at an `Int`. -/
def set : PepVal → List Nat → Int → Option PepVal
  | .int _, [], v => some (.int v)
  | .list xs, i :: rest, v =>
    match idx xs i with
    | none => none
    | some x =>
      match set x rest v with
      | none => none
      | some x' => some (.list (upd xs i x'))
  | _, _, _ => none

/-- Helper: updating position `i` installs the new element there,
    provided `i` was valid before. -/
theorem idx_upd_same (xs : List PepVal) (i : Nat) (x' : PepVal)
    (h : (idx xs i).isSome = true) :
    idx (upd xs i x') i = some x' := by
  induction xs generalizing i with
  | nil => simp [idx] at h
  | cons x xs ih =>
    cases i with
    | zero => simp [idx, upd]
    | succ n => simp [idx, upd] at h ⊢; exact ih n h

/-- Helper: updating position `i` leaves every other position `j`
    observationally unchanged. -/
theorem idx_upd_other (xs : List PepVal) (i j : Nat) (x' : PepVal)
    (h : i ≠ j) :
    idx (upd xs i x') j = idx xs j := by
  induction xs generalizing i j with
  | nil => simp [idx, upd]
  | cons x xs ih =>
    cases i with
    | zero =>
      cases j with
      | zero => simp at h
      | succ m => simp [idx, upd]
    | succ n =>
      cases j with
      | zero => simp [idx, upd]
      | succ m =>
        simp [idx, upd]
        apply ih
        simp at h ⊢
        exact h

/-- A copy-then-edit snapshot: `orig` is edited in place-shape,
    `copy` is the earlier logical copy. `editOrig` only ever rebuilds
    `orig`; `copy` is threaded through untouched by construction. -/
structure Snap where
  orig : PepVal
  copy : PepVal
  deriving DecidableEq, Repr

def editOrig (s : Snap) (p : List Nat) (v : Int) : Option Snap :=
  match set s.orig p v with
  | none => none
  | some o' => some { orig := o', copy := s.copy }

/-- Editing only ever rebuilds `orig`; the stored copy is preserved
    definitionally by `editOrig`. -/
theorem editOrig_copy (s : Snap) (p : List Nat) (v : Int) (s' : Snap)
    (h : editOrig s p v = some s') : s'.copy = s.copy := by
  simp only [editOrig] at h
  cases hset : _root_.set s.orig p v with
  | none => simp [hset] at h
  | some o' =>
    simp [hset] at h
    subst s'
    rfl

/-- THEOREM 1 (edit takes effect): a legal edit observably installs the
    new scalar at the edited path. -/
theorem edit_takes_effect (a : PepVal) (p : List Nat) (v : Int) (a' : PepVal)
    (h : set a p v = some a') :
    get a' p = some (.int v) := by
  induction p generalizing a a' with
  | nil =>
    cases a with
    | int _ => simp_all [_root_.set, _root_.get]
    | bool _ => simp [_root_.set] at h
    | list _ => simp [_root_.set] at h
  | cons i rest ih =>
    cases a with
    | int _ => simp [_root_.set] at h
    | bool _ => simp [_root_.set] at h
    | list xs =>
      have h' := h
      simp only [_root_.set] at h'
      cases hidx : idx xs i with
      | none => simp_all
      | some x =>
        simp only [hidx] at h'
        cases hset : _root_.set x rest v with
        | none => simp_all
        | some x' =>
          simp only [hset] at h'
          have ha : a' = .list (upd xs i x') := by
            injection h' with h2
            exact h2.symm
          rw [ha]
          simp only [_root_.get]
          have hstep : idx (upd xs i x') i = some x' :=
            idx_upd_same xs i x' (by simp [hidx])
          rw [hstep]
          show get x' rest = some (.int v)
          exact ih x x' hset

/-- THEOREM 2 (copy independence, DEC-001): editing the original of a
    copy-then-edit snapshot leaves every observation of the earlier
    copy identical to the pre-edit original. The proof is short because
    `editOrig` rebuilds only `orig` (see `editOrig_copy`); the modelling
    substance is (a) the executable non-vacuity checks below and (b) the
    contrasting aliased model in `AliasedCounterexample.lean`, where the
    analogous statement FAILS. -/
theorem copy_preserved (s : Snap) (hcopy : s.copy = s.orig)
    (p : List Nat) (v : Int) (s' : Snap)
    (hedit : editOrig s p v = some s') (q : List Nat) :
    get s'.copy q = get s.orig q := by
  have hcc := editOrig_copy s p v s' hedit
  rw [hcc, hcopy]

/-! ## Non-vacuity: the model expresses genuine edits, not no-ops. -/

/-- Concrete DEC-001 scenario mirroring interpreter probe P1:
    a list of three `Int`s with element 0 rewritten from 1 to 99. -/
def exOrig : PepVal := .list [.int 1, .int 2, .int 3]
def exCopy : PepVal := exOrig
def exPath : List Nat := [0]
def exNew : Int := 99

/-- The edit is legal and computes to the rewritten list.
    `#eval` witnesses this on this host. -/
def exEdited : Option PepVal := set exOrig exPath exNew
#eval exEdited
-- Expected: `some (PepVal.list [PepVal.int 99, PepVal.int 2, PepVal.int 3])`

/-- The edit is genuine: the result differs from the original. -/
example : exEdited ≠ some exOrig := by decide

/-- The copy still observes the pre-edit value at the edited path. -/
example : get exCopy exPath = some (.int 1) := rfl

/-- After the edit, the original observes the new value there
    (the executable shadow of THEOREM 1 for this instance). -/
example : (set exOrig exPath exNew) = some (.list [.int 99, .int 2, .int 3]) := rfl
