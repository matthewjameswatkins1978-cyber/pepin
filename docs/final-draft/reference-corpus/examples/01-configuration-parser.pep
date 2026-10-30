// PROPOSED PEP SYNTAX FIXTURE; not expected to compile on the current seed.
use std.text as text
use std.int as integer

type Config {
    retries: Int
    active: Bool
}

type ConfigError =
    MissingLine |
    InvalidCount(Str) |
    InvalidFlag(Str)

fn parse_count(source: Str) -> Result[Int, ConfigError] {
    match integer.parse(source) {
        Ok(number) => Ok(number)
        Err(_) => Err(InvalidCount(source))
    }
}

pub fn parse_config(source: Str) -> Result[Config, ConfigError] {
    let lines = text.lines(source)

    let count_line = match lines.get(0) {
        Some(value) => value
        None => return Err(MissingLine)
    }

    let flag_line = match lines.get(1) {
        Some(value) => value
        None => return Err(MissingLine)
    }

    let retries = try parse_count(count_line)

    let active = if flag_line == "on" {
        true
    } else if flag_line == "off" {
        false
    } else {
        return Err(InvalidFlag(flag_line))
    }

    Ok(Config {
        retries: retries
        active: active
    })
}
