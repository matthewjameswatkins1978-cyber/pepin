// Agent-4 UTF-8 probe: exercises pep_utf8_validate/decode/encode over
// fixed boundary vectors and prints one deterministic line per check.
// The Python suite asserts the exact output; the vectors mirror the Pep
// lexer model boundaries (overlongs, surrogates, >U+10FFFF, truncations).
#include <stdio.h>

#include "pep_utf8.h"

static void check_validate(const char *s, size_t n)
{
    size_t off = 0;
    int status = pep_utf8_validate(s, n, &off);
    if (status == PEP_UTF8_OK) {
        (void)printf("v ok\n");
    } else {
        (void)printf("v err %llu\n", (unsigned long long)off);
    }
}

static void check_decode(const char *s, size_t n)
{
    unsigned int cp = 0;
    size_t width = pep_utf8_decode(s, n, &cp);
    if (width == 0) {
        (void)printf("d invalid\n");
    } else {
        (void)printf("d %X %llu\n", cp, (unsigned long long)width);
    }
}

static void check_encode(unsigned int cp)
{
    char out[4] = { 0, 0, 0, 0 };
    size_t width = pep_utf8_encode(cp, out);
    size_t i;
    if (width == 0) {
        (void)printf("e invalid\n");
        return;
    }
    (void)printf("e %llu ", (unsigned long long)width);
    for (i = 0; i < width; i++) {
        (void)printf("%02X", (unsigned char)out[i]);
    }
    (void)printf("\n");
}

int main(void)
{
    static const char ascii[] = "hello";
    static const char e_acute[] = "\xC3\xA9";
    static const char euro[] = "\xE2\x82\xAC";
    static const char smile[] = "\xF0\x9F\x98\x80";
    static const char lone_cont[] = "\x80";
    static const char overlong_slash[] = "\xC0\xAF";
    static const char overlong_max[] = "\xC1\xBF";
    static const char e0_low[] = "\xE0\x9F\x80";
    static const char surrogate[] = "\xED\xA0\x80";
    static const char too_big[] = "\xF4\x90\x80\x80";
    static const char f5_lead[] = "\xF5\x80\x80\x80";
    static const char trunc3[] = "\xE2\x82";
    static const char ff_mid[] = "a\xFF" "b";
    static const char bad_cont[] = "\xC3\x28";
    static const char trunc4[] = "\xF0\x9F\x98";
    static const char letter_a[] = "A";

    check_validate("", 0);
    check_validate(ascii, sizeof ascii - 1);
    check_validate(e_acute, sizeof e_acute - 1);
    check_validate(euro, sizeof euro - 1);
    check_validate(smile, sizeof smile - 1);
    check_validate(lone_cont, sizeof lone_cont - 1);
    check_validate(overlong_slash, sizeof overlong_slash - 1);
    check_validate(overlong_max, sizeof overlong_max - 1);
    check_validate(e0_low, sizeof e0_low - 1);
    check_validate(surrogate, sizeof surrogate - 1);
    check_validate(too_big, sizeof too_big - 1);
    check_validate(f5_lead, sizeof f5_lead - 1);
    check_validate(trunc3, sizeof trunc3 - 1);
    check_validate(ff_mid, sizeof ff_mid - 1);
    check_validate(bad_cont, sizeof bad_cont - 1);
    check_validate(trunc4, sizeof trunc4 - 1);

    check_decode(letter_a, sizeof letter_a - 1);
    check_decode(e_acute, sizeof e_acute - 1);
    check_decode(euro, sizeof euro - 1);
    check_decode(smile, sizeof smile - 1);
    check_decode(lone_cont, sizeof lone_cont - 1);
    check_decode(trunc3, sizeof trunc3 - 1);
    check_decode("", 0);

    check_encode(0x41);
    check_encode(0xE9);
    check_encode(0x20AC);
    check_encode(0x1F600);
    check_encode(0xD800);
    check_encode(0xDFFF);
    check_encode(0x110000);
    check_encode(0x10FFFF);
    return 0;
}
