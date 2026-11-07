fn build() -> List[Int] {
  var xs: List[Int] = [1, 2, 3]
  return xs
}

fn total(xs: List[Int]) -> Int {
  var n = 0
  for x in xs {
    n = n + x
  }
  return n
}

fn main() -> Int {
  var xs: List[Int] = [1, 2, 3]
  var t = total(xs)
  return t
}
