// PROPOSED PEP SYNTAX FIXTURE; task.Error and cancellation are not implemented contracts.
use std.net.http as http
use std.task as task

type Replies {
    left: Str
    right: Str
}

async fn fetch(url: Str) -> Result[Str, http.Error]
    uses net.read
{
    http.get_text(url)
}

// 'await' is proposed to yield Result[T, task.Error[E]], distinct from E.
// 'try' may propagate that exact task error; it does not silently convert E.
pub async fn gather() -> Result[Replies, task.Error[http.Error]]
    uses net.read
{
    task {
        let left_job = spawn fetch("https://example.invalid/left")
        let right_job = spawn fetch("https://example.invalid/right")

        let left = try await left_job
        let right = try await right_job

        Ok(Replies {
            left: left
            right: right
        })
    }
}

// Required safety scenario: if left_job fails, right_job must be cancelled
// and drained by the task scope before the function returns an error.
// The .invalid URLs are deliberate placeholders, not working endpoints.
