// PROPOSED PEP SYNTAX FIXTURE; HTTP types, host grants and effects are future APIs.
use std.net.http as http

// Pure request transformation: no network permission or effect required.
pub fn handle(request: http.Request) -> http.Response {
    if request.method != http.Method.Get {
        return http.Response.text(405, "method not allowed")
    }

    if request.path == "/health" {
        return http.Response.text(200, "healthy")
    }

    http.Response.text(404, "not found")
}

// 'uses' sets an effect ceiling; it does not grant runtime network authority.
pub fn main() -> Result[Unit, http.Error]
    uses net.listen, net.read, net.write
{
    let server = try http.listen("127.0.0.1", 8080)
    http.serve(take server, handle)
}
