fn list_int_sum(values: List[Int]) -> Int {
  var total = 0
  for item in values { total = total + item }
  return total
}

fn list_int_product(values: List[Int]) -> Int {
  var product = 1
  for item in values { product = product * item }
  return product
}

fn list_int_product_nonzero(values: List[Int]) -> Int {
  var product = 1
  for item in values { product = if item != 0 { product * item } else { product } }
  return product
}

fn list_bool_prefix_length_of(values: List[Bool], expected: Bool) -> Int {
  var prefix = 0
  var ended = false
  for item in values {
    prefix = if !ended && item == expected { prefix + 1 } else { prefix }
    ended = ended || item != expected
  }
  return prefix
}

fn list_bool_false_prefix_length(values: List[Bool]) -> Int {
  var prefix = 0
  var ended = false
  for item in values {
    prefix = if !ended && !item { prefix + 1 } else { prefix }
    ended = ended || item
  }
  return prefix
}

fn list_bool_true_prefix_length(values: List[Bool]) -> Int {
  var prefix = 0
  var ended = false
  for item in values {
    prefix = if !ended && item { prefix + 1 } else { prefix }
    ended = ended || !item
  }
  return prefix
}

fn list_bool_suffix_length_of(values: List[Bool], expected: Bool) -> Int {
  var suffix = 0
  for item in values { suffix = if item == expected { suffix + 1 } else { 0 } }
  return suffix
}

fn list_bool_true_suffix_length(values: List[Bool]) -> Int {
  var suffix = 0
  for item in values { suffix = if item { suffix + 1 } else { 0 } }
  return suffix
}

fn list_bool_false_suffix_length(values: List[Bool]) -> Int {
  var suffix = 0
  for item in values { suffix = if !item { suffix + 1 } else { 0 } }
  return suffix
}

fn list_bool_count_true(values: List[Bool]) -> Int {
  var total = 0
  for item in values { total = if item { total + 1 } else { total } }
  return total
}

fn list_bool_count_false(values: List[Bool]) -> Int {
  var total = 0
  for item in values { total = if !item { total + 1 } else { total } }
  return total
}

fn list_bool_any_false(values: List[Bool]) -> Bool {
  var found = false
  for item in values { found = found || !item }
  return found
}

fn list_bool_any(values: List[Bool]) -> Bool {
  var found = false
  for item in values { found = found || item }
  return found
}

fn list_bool_none(values: List[Bool]) -> Bool {
  return !contains(values, true)
}

fn list_bool_all(values: List[Bool]) -> Bool {
  var all = true
  for item in values { all = all && item }
  return all
}

fn list_bool_count_adjacent_equal_pairs(values: List[Bool]) -> Int {
  var pairs = 0
  var hasPrevious = false
  var previous = false
  for item in values {
    pairs = if hasPrevious && item == previous { pairs + 1 } else { pairs }
    previous = item
    hasPrevious = true
  }
  return pairs
}

fn list_bool_is_alternating(values: List[Bool]) -> Bool {
  var alternating = true
  var hasPrevious = false
  var previous = false
  for item in values {
    alternating = if hasPrevious && item == previous { false } else { alternating }
    previous = item
    hasPrevious = true
  }
  return alternating
}

fn list_bool_is_constant(values: List[Bool]) -> Bool {
  var constant = true
  var hasPrevious = false
  var previous = false
  for item in values {
    constant = if hasPrevious && !(item == previous) { false } else { constant }
    previous = item
    hasPrevious = true
  }
  return constant
}

fn list_bool_all_equal(values: List[Bool], expected: Bool) -> Bool {
  var all = true
  for item in values { all = all && item == expected }
  return all
}

fn list_bool_count_equal(values: List[Bool], expected: Bool) -> Int {
  var total = 0
  for item in values { total = if item == expected { total + 1 } else { total } }
  return total
}

fn list_bool_count_not_equal(values: List[Bool], expected: Bool) -> Int {
  var total = 0
  for item in values { total = if item != expected { total + 1 } else { total } }
  return total
}

fn list_bool_longest_run_of(values: List[Bool], expected: Bool) -> Int {
  var current = 0
  var longest = 0
  for item in values {
    current = if item == expected { current + 1 } else { 0 }
    longest = if current <= longest { longest } else { current }
  }
  return longest
}

fn list_bool_is_non_decreasing(values: List[Bool]) -> Bool {
  var ordered = true
  var seenTrue = false
  for item in values {
    ordered = if !item && seenTrue { false } else { ordered }
    seenTrue = seenTrue || item
  }
  return ordered
}

fn list_bool_is_non_increasing(values: List[Bool]) -> Bool {
  var ordered = true
  var seenFalse = false
  for item in values {
    ordered = if item && seenFalse { false } else { ordered }
    seenFalse = seenFalse || !item
  }
  return ordered
}

fn list_bool_is_monotonic(values: List[Bool]) -> Bool {
  var monotonic = true
  var hasPrevious = false
  var previous = false
  var seenTransition = false
  for item in values {
    monotonic = if hasPrevious && item != previous && seenTransition { false } else { monotonic }
    seenTransition = seenTransition || (hasPrevious && item != previous)
    previous = item
    hasPrevious = true
  }
  return monotonic
}

fn list_bool_all_false(values: List[Bool]) -> Bool {
  var all = true
  for item in values { all = all && !item }
  return all
}

fn list_int_count_nonzero(values: List[Int]) -> Int {
  var total = 0
  for item in values { total = if item != 0 { total + 1 } else { total } }
  return total
}

fn list_int_count_zero(values: List[Int]) -> Int {
  var total = 0
  for item in values { total = if item == 0 { total + 1 } else { total } }
  return total
}

fn list_int_count_equal(values: List[Int], expected: Int) -> Int {
  var total = 0
  for item in values { total = if item == expected { total + 1 } else { total } }
  return total
}

fn list_int_sum_equal(values: List[Int], expected: Int) -> Int {
  var total = 0
  for item in values { total = if item == expected { total + item } else { total } }
  return total
}

fn list_int_sum_not_equal(values: List[Int], expected: Int) -> Int {
  var total = 0
  for item in values { total = if item != expected { total + item } else { total } }
  return total
}

fn list_int_all_equal(values: List[Int], expected: Int) -> Bool {
  var all = true
  for item in values { all = all && (item == expected) }
  return all
}

fn list_int_count_not_equal(values: List[Int], expected: Int) -> Int {
  var total = 0
  for item in values { total = if item != expected { total + 1 } else { total } }
  return total
}

fn list_int_any_between(values: List[Int], lower: Int, upper: Int) -> Bool {
  var found = false
  for item in values { found = found || (lower <= item && item <= upper) }
  return found
}

fn list_int_all_between(values: List[Int], lower: Int, upper: Int) -> Bool {
  var all = true
  for item in values { all = all && (lower <= item && item <= upper) }
  return all
}

fn list_int_index_of_between(values: List[Int], lower: Int, upper: Int) -> Int {
  var index = 0
  var foundAt = -1
  for item in values {
    foundAt = if foundAt == -1 && lower <= item && item <= upper { index } else { foundAt }
    index = index + 1
  }
  return foundAt
}

fn list_int_last_index_of_between(values: List[Int], lower: Int, upper: Int) -> Int {
  var index = 0
  var foundAt = -1
  for item in values {
    foundAt = if lower <= item && item <= upper { index } else { foundAt }
    index = index + 1
  }
  return foundAt
}

fn list_int_prefix_length_between(values: List[Int], lower: Int, upper: Int) -> Int {
  var active = true
  var length = 0
  for item in values {
    length = if active && lower <= item && item <= upper { length + 1 } else { length }
    active = active && lower <= item && item <= upper
  }
  return length
}

fn list_int_suffix_length_between(values: List[Int], lower: Int, upper: Int) -> Int {
  var length = 0
  for item in values {
    length = if lower <= item && item <= upper { length + 1 } else { 0 }
  }
  return length
}

fn list_int_min_index_between(values: List[Int], lower: Int, upper: Int) -> Int {
  var index = 0
  var minimumIndex = -1
  var minimum = 0
  var found = false
  for item in values {
    minimumIndex = if lower <= item && item <= upper && (!found || !(minimum <= item)) { index } else { minimumIndex }
    minimum = if lower <= item && item <= upper && (!found || !(minimum <= item)) { item } else { minimum }
    found = found || (lower <= item && item <= upper)
    index = index + 1
  }
  return minimumIndex
}

fn list_int_max_index_between(values: List[Int], lower: Int, upper: Int) -> Int {
  var index = 0
  var maximumIndex = -1
  var maximum = 0
  var found = false
  for item in values {
    maximumIndex = if lower <= item && item <= upper && (!found || !(item <= maximum)) { index } else { maximumIndex }
    maximum = if lower <= item && item <= upper && (!found || !(item <= maximum)) { item } else { maximum }
    found = found || (lower <= item && item <= upper)
    index = index + 1
  }
  return maximumIndex
}

fn list_int_count_between(values: List[Int], lower: Int, upper: Int) -> Int {
  var total = 0
  for item in values {
    total = if lower <= item && item <= upper { total + 1 } else { total }
  }
  return total
}

fn list_int_product_between(values: List[Int], lower: Int, upper: Int) -> Int {
  var product = 1
  for item in values {
    product = if lower <= item && item <= upper { product * item } else { product }
  }
  return product
}

fn list_int_sum_between(values: List[Int], lower: Int, upper: Int) -> Int {
  var total = 0
  for item in values {
    total = if lower <= item && item <= upper { total + item } else { total }
  }
  return total
}

fn list_int_count_outside(values: List[Int], lower: Int, upper: Int) -> Int {
  var total = 0
  for item in values {
    total = if !(lower <= item && item <= upper) { total + 1 } else { total }
  }
  return total
}

fn list_int_product_outside(values: List[Int], lower: Int, upper: Int) -> Int {
  var product = 1
  for item in values {
    product = if !(lower <= item && item <= upper) { product * item } else { product }
  }
  return product
}

fn list_int_sum_outside(values: List[Int], lower: Int, upper: Int) -> Int {
  var total = 0
  for item in values {
    total = if !(lower <= item && item <= upper) { total + item } else { total }
  }
  return total
}

fn list_bool_longest_run(values: List[Bool]) -> Int {
  var current = 0
  var longest = 0
  var previous = false
  for item in values {
    current = if item == previous { current + 1 } else { 1 }
    longest = if current <= longest { longest } else { current }
    previous = item
  }
  return longest
}

fn list_bool_count_false_runs(values: List[Bool]) -> Int {
  var runs = 0
  var previous = true
  for item in values {
    runs = if !item && previous { runs + 1 } else { runs }
    previous = item
  }
  return runs
}

fn list_bool_count_runs_of(values: List[Bool], expected: Bool) -> Int {
  var runs = 0
  var hasPrevious = false
  var previous = false
  for item in values {
    runs = if item == expected && (!hasPrevious || previous != expected) { runs + 1 } else { runs }
    previous = item
    hasPrevious = true
  }
  return runs
}

fn list_bool_count_true_runs(values: List[Bool]) -> Int {
  var runs = 0
  var previous = false
  for item in values {
    runs = if item && !previous { runs + 1 } else { runs }
    previous = item
  }
  return runs
}

fn list_bool_longest_true_run(values: List[Bool]) -> Int {
  var current = 0
  var longest = 0
  for item in values {
    current = if item { current + 1 } else { 0 }
    longest = if current <= longest { longest } else { current }
  }
  return longest
}

fn list_bool_longest_false_run(values: List[Bool]) -> Int {
  var current = 0
  var longest = 0
  for item in values {
    current = if !item { current + 1 } else { 0 }
    longest = if current <= longest { longest } else { current }
  }
  return longest
}

fn list_bool_count_transitions(values: List[Bool]) -> Int {
  var transitions = 0
  var hasPrevious = false
  var previous = false
  for item in values {
    transitions = if hasPrevious && !(item == previous) { transitions + 1 } else { transitions }
    previous = item
    hasPrevious = true
  }
  return transitions
}

fn list_bool_count_runs(values: List[Bool]) -> Int {
  var runs = 0
  var hasPrevious = false
  var previous = false
  for item in values {
    runs = if !hasPrevious { runs + 1 } else { if item != previous { runs + 1 } else { runs } }
    previous = item
    hasPrevious = true
  }
  return runs
}

fn list_int_longest_run(values: List[Int]) -> Int {
  var current = 0
  var longest = 0
  var previous = 0
  for item in values {
    current = if item == previous { current + 1 } else { 1 }
    longest = if current <= longest { longest } else { current }
    previous = item
  }
  return longest
}

fn list_int_count_adjacent_equal_pairs(values: List[Int]) -> Int {
  var pairs = 0
  var hasPrevious = false
  var previous = 0
  for item in values {
    pairs = if hasPrevious && item == previous { pairs + 1 } else { pairs }
    previous = item
    hasPrevious = true
  }
  return pairs
}

fn list_int_is_constant(values: List[Int]) -> Bool {
  var constant = true
  var hasPrevious = false
  var previous = 0
  for item in values {
    constant = if hasPrevious && !(item == previous) { false } else { constant }
    previous = item
    hasPrevious = true
  }
  return constant
}

fn list_int_is_non_decreasing(values: List[Int]) -> Bool {
  var ordered = true
  var hasPrevious = false
  var previous = 0
  for item in values {
    ordered = if hasPrevious && !(previous <= item) { false } else { ordered }
    previous = item
    hasPrevious = true
  }
  return ordered
}

fn list_int_is_non_increasing(values: List[Int]) -> Bool {
  var ordered = true
  var hasPrevious = false
  var previous = 0
  for item in values {
    ordered = if hasPrevious && !(item <= previous) { false } else { ordered }
    previous = item
    hasPrevious = true
  }
  return ordered
}

fn list_int_is_strictly_increasing(values: List[Int]) -> Bool {
  var increasing = true
  var hasPrevious = false
  var previous = 0
  for item in values {
    increasing = if hasPrevious && item <= previous { false } else { increasing }
    previous = item
    hasPrevious = true
  }
  return increasing
}

fn list_int_is_strictly_decreasing(values: List[Int]) -> Bool {
  var decreasing = true
  var hasPrevious = false
  var previous = 0
  for item in values {
    decreasing = if hasPrevious && previous <= item { false } else { decreasing }
    previous = item
    hasPrevious = true
  }
  return decreasing
}

fn list_int_count_sign_changes(values: List[Int]) -> Int {
  var changes = 0
  var hasPreviousNonzero = false
  var previousPositive = false
  for item in values {
    changes = if item != 0 && hasPreviousNonzero && (1 <= item) != previousPositive { changes + 1 } else { changes }
    previousPositive = if item != 0 { 1 <= item } else { previousPositive }
    hasPreviousNonzero = hasPreviousNonzero || item != 0
  }
  return changes
}

fn list_int_count_rises(values: List[Int]) -> Int {
  var rises = 0
  var hasPrevious = false
  var previous = 0
  for item in values {
    rises = if hasPrevious && !(item <= previous) { rises + 1 } else { rises }
    previous = item
    hasPrevious = true
  }
  return rises
}

fn list_int_count_falls(values: List[Int]) -> Int {
  var falls = 0
  var hasPrevious = false
  var previous = 0
  for item in values {
    falls = if hasPrevious && !(previous <= item) { falls + 1 } else { falls }
    previous = item
    hasPrevious = true
  }
  return falls
}

fn list_int_count_runs(values: List[Int]) -> Int {
  var runs = 0
  var hasPrevious = false
  var previous = 0
  for item in values {
    runs = if !hasPrevious { runs + 1 } else { if item != previous { runs + 1 } else { runs } }
    previous = item
    hasPrevious = true
  }
  return runs
}

fn list_int_sum_less_than(values: List[Int], upper: Int) -> Int {
  var total = 0
  for item in values { total = if !(upper <= item) { total + item } else { total } }
  return total
}

fn list_int_sum_at_most(values: List[Int], upper: Int) -> Int {
  var total = 0
  for item in values { total = if item <= upper { total + item } else { total } }
  return total
}

fn list_int_sum_greater_than(values: List[Int], lower: Int) -> Int {
  var total = 0
  for item in values { total = if !(item <= lower) { total + item } else { total } }
  return total
}

fn list_int_sum_at_least(values: List[Int], lower: Int) -> Int {
  var total = 0
  for item in values { total = if lower <= item { total + item } else { total } }
  return total
}

fn list_int_count_at_most(values: List[Int], upper: Int) -> Int {
  var total = 0
  for item in values { total = if item <= upper { total + 1 } else { total } }
  return total
}

fn list_int_count_greater_than(values: List[Int], lower: Int) -> Int {
  var total = 0
  for item in values { total = if !(item <= lower) { total + 1 } else { total } }
  return total
}

fn list_int_any_zero(values: List[Int]) -> Bool {
  var found = false
  for item in values { found = found || (item == 0) }
  return found
}

fn list_int_any_nonzero(values: List[Int]) -> Bool {
  var found = false
  for item in values { found = found || (item != 0) }
  return found
}

fn list_int_count_negative(values: List[Int]) -> Int {
  var total = 0
  for item in values { total = if item <= -1 { total + 1 } else { total } }
  return total
}

fn list_int_any_negative(values: List[Int]) -> Bool {
  var found = false
  for item in values { found = found || item <= -1 }
  return found
}

fn list_int_all_negative(values: List[Int]) -> Bool {
  var all = true
  for item in values { all = all && item <= -1 }
  return all
}

fn list_int_all_nonnegative(values: List[Int]) -> Bool {
  var all = true
  for item in values { all = all && !(item <= -1) }
  return all
}

fn list_int_all_nonpositive(values: List[Int]) -> Bool {
  var all = true
  for item in values { all = all && item <= 0 }
  return all
}

fn list_int_all_positive(values: List[Int]) -> Bool {
  var all = true
  for item in values { all = all && (!(item <= 0)) }
  return all
}

fn list_int_any_positive(values: List[Int]) -> Bool {
  var found = false
  for item in values { found = found || (!(item <= 0)) }
  return found
}

fn list_int_sum_positive(values: List[Int]) -> Int {
  var total = 0
  for item in values { total = if item <= 0 { total } else { total + item } }
  return total
}

fn list_int_sum_negative(values: List[Int]) -> Int {
  var total = 0
  for item in values { total = if item <= -1 { total + item } else { total } }
  return total
}

fn list_int_count_positive(values: List[Int]) -> Int {
  var total = 0
  for item in values { total = if !(item <= 0) { total + 1 } else { total } }
  return total
}

fn list_int_first_or(values: List[Int], fallback: Int) -> Int {
  var first = fallback
  var found = false
  for item in values {
    first = if !found { item } else { first }
    found = true
  }
  return first
}

fn list_int_last_or(values: List[Int], fallback: Int) -> Int {
  var last = fallback
  for item in values { last = item }
  return last
}

fn list_int_index_of(values: List[Int], needle: Int) -> Int {
  var index = 0
  var foundAt = -1
  for item in values {
    foundAt = if foundAt == -1 && item == needle { index } else { foundAt }
    index = index + 1
  }
  return foundAt
}

fn list_int_last_index_of(values: List[Int], needle: Int) -> Int {
  var index = 0
  var foundAt = -1
  for item in values {
    foundAt = if item == needle { index } else { foundAt }
    index = index + 1
  }
  return foundAt
}

fn list_int_contains(values: List[Int], needle: Int) -> Bool {
  return contains(values, needle)
}

fn list_int_min_between(values: List[Int], lower: Int, upper: Int, fallback: Int) -> Int {
  var found = false
  var minimum = fallback
  for item in values {
    minimum = if lower <= item && item <= upper && (!found || item <= minimum) { item } else { minimum }
    found = found || (lower <= item && item <= upper)
  }
  return minimum
}

fn list_int_max_between(values: List[Int], lower: Int, upper: Int, fallback: Int) -> Int {
  var found = false
  var maximum = fallback
  for item in values {
    maximum = if lower <= item && item <= upper && (!found || !(item <= maximum)) { item } else { maximum }
    found = found || (lower <= item && item <= upper)
  }
  return maximum
}

fn list_int_min_outside(values: List[Int], lower: Int, upper: Int, fallback: Int) -> Int {
  var found = false
  var minimum = fallback
  for item in values {
    minimum = if !(lower <= item && item <= upper) && (!found || item <= minimum) { item } else { minimum }
    found = found || !(lower <= item && item <= upper)
  }
  return minimum
}

fn list_int_max_outside(values: List[Int], lower: Int, upper: Int, fallback: Int) -> Int {
  var found = false
  var maximum = fallback
  for item in values {
    maximum = if !(lower <= item && item <= upper) && (!found || !(item <= maximum)) { item } else { maximum }
    found = found || !(lower <= item && item <= upper)
  }
  return maximum
}

fn list_int_first_outside(values: List[Int], lower: Int, upper: Int, fallback: Int) -> Int {
  var found = false
  var first = fallback
  for item in values {
    first = if !found && !(lower <= item && item <= upper) { item } else { first }
    found = found || !(lower <= item && item <= upper)
  }
  return first
}

fn list_int_index_of_outside(values: List[Int], lower: Int, upper: Int) -> Int {
  var index = 0
  var foundAt = -1
  for item in values {
    foundAt = if foundAt == -1 && !(lower <= item && item <= upper) { index } else { foundAt }
    index = index + 1
  }
  return foundAt
}

fn list_int_last_index_of_outside(values: List[Int], lower: Int, upper: Int) -> Int {
  var index = 0
  var foundAt = -1
  for item in values {
    foundAt = if !(lower <= item && item <= upper) { index } else { foundAt }
    index = index + 1
  }
  return foundAt
}

fn list_int_last_outside(values: List[Int], lower: Int, upper: Int, fallback: Int) -> Int {
  var last = fallback
  for item in values {
    last = if !(lower <= item && item <= upper) { item } else { last }
  }
  return last
}

fn list_int_any_outside(values: List[Int], lower: Int, upper: Int) -> Bool {
  var found = false
  for item in values {
    found = found || !(lower <= item && item <= upper)
  }
  return found
}

fn list_int_min_or(values: List[Int], fallback: Int) -> Int {
  var found = false
  var minimum = fallback
  for item in values {
    minimum = if !found || item <= minimum { item } else { minimum }
    found = true
  }
  return minimum
}

fn list_int_max_or(values: List[Int], fallback: Int) -> Int {
  var found = false
  var maximum = fallback
  for item in values {
    maximum = if !found || !(item <= maximum) { item } else { maximum }
    found = true
  }
  return maximum
}

fn list_bool_index_of(values: List[Bool], needle: Bool) -> Int {
  var index = 0
  var foundAt = -1
  for item in values {
    foundAt = if foundAt == -1 && item == needle { index } else { foundAt }
    index = index + 1
  }
  return foundAt
}

fn list_bool_last_index_of(values: List[Bool], needle: Bool) -> Int {
  var index = 0
  var foundAt = -1
  for item in values {
    foundAt = if item == needle { index } else { foundAt }
    index = index + 1
  }
  return foundAt
}

fn list_bool_has_true_majority(values: List[Bool]) -> Bool {
  var balance = 0
  for item in values {
    balance = if item { balance + 1 } else { balance - 1 }
  }
  return !(balance <= 0)
}

fn list_bool_last_or(values: List[Bool], fallback: Bool) -> Bool {
  var last = fallback
  for item in values { last = item }
  return last
}

fn list_bool_first_or(values: List[Bool], fallback: Bool) -> Bool {
  var first = fallback
  var found = false
  for item in values {
    first = if !found { item } else { first }
    found = true
  }
  return first
}

fn list_bool_contains(values: List[Bool], needle: Bool) -> Bool {
  return contains(values, needle)
}
