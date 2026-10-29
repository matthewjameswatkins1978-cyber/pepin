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

fn list_int_count_between(values: List[Int], lower: Int, upper: Int) -> Int {
  var total = 0
  for item in values {
    total = if lower <= item && item <= upper { total + 1 } else { total }
  }
  return total
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

fn list_bool_longest_true_run(values: List[Bool]) -> Int {
  var current = 0
  var longest = 0
  for item in values {
    current = if item { current + 1 } else { 0 }
    longest = if current <= longest { longest } else { current }
  }
  return longest
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

fn list_int_sum_at_most(values: List[Int], upper: Int) -> Int {
  var total = 0
  for item in values { total = if item <= upper { total + item } else { total } }
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
  for item in values { return item }
  return fallback
}

fn list_int_last_or(values: List[Int], fallback: Int) -> Int {
  var last = fallback
  for item in values { last = item }
  return last
}

fn list_int_index_of(values: List[Int], needle: Int) -> Int {
  var index = 0
  for item in values {
    if item == needle { return index } else { index = index + 1 }
  }
  return -1
}

fn list_int_last_index_of(values: List[Int], needle: Int) -> Int {
  var index = 0
  var foundAt = -1
  for item in values {
    if item == needle {
      foundAt = index
      index = index + 1
    } else {
      index = index + 1
    }
  }
  return foundAt
}

fn list_int_contains(values: List[Int], needle: Int) -> Bool {
  return contains(values, needle)
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

fn list_bool_first_or(values: List[Bool], fallback: Bool) -> Bool {
  for item in values { return item }
  return fallback
}

fn list_bool_contains(values: List[Bool], needle: Bool) -> Bool {
  return contains(values, needle)
}
