// PROPOSED PEP SYNTAX FIXTURE; Map APIs, edit semantics and checked overflow need acceptance.
use std.collections.map as map

type Reading {
    sensor: Str
    value: Int
}

type Summary {
    count: Int
    total: Int
    minimum: Int
    maximum: Int
}

pub fn summarise(readings: List[Reading]) -> Option[Summary] {
    let first = match readings.get(0) {
        Some(value) => value
        None => return None
    }

    var count = 0
    var total = 0
    var minimum = first.value
    var maximum = first.value

    for reading in readings {
        count = count + 1
        total = total + reading.value

        if reading.value < minimum {
            minimum = reading.value
        }
        if reading.value > maximum {
            maximum = reading.value
        }
    }

    Some(Summary {
        count: count
        total: total
        minimum: minimum
        maximum: maximum
    })
}

pub fn count_by_sensor(readings: List[Reading]) -> Map[Str, Int] {
    var counts: Map[Str, Int] = map.empty()

    for reading in readings {
        let previous = match map.get(counts, reading.sensor) {
            Some(value) => value
            None => 0
        }
        map.put(edit counts, reading.sensor, previous + 1)
    }

    counts
}
