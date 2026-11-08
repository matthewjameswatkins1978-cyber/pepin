// Agent-4 fragment probe: joins argv fragments with pep_textbuf_join and
// writes the result. Usage: frag_probe FRAGMENT...  Each argument is one
// fragment (like one entry of the emitter's sourceParts); the joined
// bytes go to stdout. Binary stdout (see span_probe) so assertions are
// byte-exact. There is no fragment-count or size limit beyond argv.
#include <stdio.h>

#include "pep_textbuf.h"

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

int main(int argc, char **argv)
{
    pep_textbuf_t buf;
    int status;
#ifdef _WIN32
    (void)_setmode(_fileno(stdout), _O_BINARY);
#endif
    if (pep_textbuf_init(&buf) != 0) {
        return 1;
    }
    if (argc > 1) {
        status = pep_textbuf_join(&buf, (const char *const *)&argv[1],
            (size_t)(argc - 1));
        if (status != 0) {
            pep_textbuf_free(&buf);
            return 1;
        }
    }
    status = pep_textbuf_write(&buf, stdout);
    pep_textbuf_free(&buf);
    return (status == 0) ? 0 : 1;
}
