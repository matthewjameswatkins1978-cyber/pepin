fn list_int_sum(values: List[Int]) -> Int {
  var total = 0
  for item in values { total = total + item }
  return total
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

fn list_bool_any(values: List[Bool]) -> Bool {
  var found = false
  for item in values { found = found || item }
  return found
}

fn list_bool_all(values: List[Bool]) -> Bool {
  var all = true
  for item in values { all = all && item }
  return all
}

fn list_int_contains(values: List[Int], needle: Int) -> Bool {
  return contains(values, needle)
}
