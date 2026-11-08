#include <stddef.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
typedef struct { const unsigned char *data; size_t length; } pep_source_bytes;
[[maybe_unused]] static int64_t pep_byte_at(pep_source_bytes source, int64_t offset) {
  if (source.length != 0 && source.data == NULL) { fputs("PEP_RUNTIME_INVALID_SOURCE_BYTES\n", stderr); exit(1); }
  if (offset < 0 || (uintmax_t)offset >= (uintmax_t)source.length) { fputs("PEP_RUNTIME_BYTE_RANGE\n", stderr); exit(1); }
  return (int64_t)source.data[(size_t)offset];
}
[[maybe_unused]] static int64_t pep_byte_length(pep_source_bytes source) {
  if (source.length != 0 && source.data == NULL) { fputs("PEP_RUNTIME_INVALID_SOURCE_BYTES\n", stderr); exit(1); }
  if ((uintmax_t)source.length > (uintmax_t)INT64_MAX) { fputs("PEP_RUNTIME_LENGTH_RANGE\n", stderr); exit(1); }
  return (int64_t)source.length;
}
typedef struct { const unsigned char *data; size_t length; } pep_str;
[[maybe_unused]] static _Bool pep_str_equal(pep_str left, pep_str right) {
  if ((left.length != 0 && left.data == NULL) || (right.length != 0 && right.data == NULL)) { fputs("PEP_RUNTIME_INVALID_STR\n", stderr); exit(1); }
  if (left.length != right.length) { return 0; }
  for (size_t i = 0; i < left.length; ++i) { if (left.data[i] != right.data[i]) { return 0; } }
  return 1;
}
[[maybe_unused]] static _Bool pep_str_contains(pep_str haystack, pep_str needle) {
  if ((haystack.length != 0 && haystack.data == NULL) || (needle.length != 0 && needle.data == NULL)) { fputs("PEP_RUNTIME_INVALID_STR\n", stderr); exit(1); }
  if (needle.length == 0) { return 1; }
  if (needle.length > haystack.length) { return 0; }
  size_t limit = haystack.length - needle.length;
  for (size_t i = 0; i <= limit; ++i) {
    size_t j = 0;
    while (j < needle.length && haystack.data[i + j] == needle.data[j]) { ++j; }
    if (j == needle.length) { return 1; }
  }
  return 0;
}
#define PEP_STR_CONCAT_CAPACITY 4096
[[maybe_unused]] static pep_str pep_str_concat(pep_str left, pep_str right) {
  if ((left.length != 0 && left.data == NULL) || (right.length != 0 && right.data == NULL)) { fputs("PEP_RUNTIME_INVALID_STR\n", stderr); exit(1); }
  if (left.length > PEP_STR_CONCAT_CAPACITY || right.length > PEP_STR_CONCAT_CAPACITY - left.length) { fputs("PEP_RUNTIME_STR_CONCAT_RANGE\n", stderr); exit(1); }
  static unsigned char pep_concat_pool[PEP_STR_CONCAT_CAPACITY];
  static size_t pep_concat_used = 0;
  unsigned char *out = pep_concat_pool + pep_concat_used;
  for (size_t i = 0; i < left.length; ++i) { out[i] = left.data[i]; }
  for (size_t i = 0; i < right.length; ++i) { out[left.length + i] = right.data[i]; }
  pep_concat_used += left.length + right.length;
  return (pep_str){ .data = out, .length = left.length + right.length };
}
[[maybe_unused]] static pep_str pep_utf8_slice(pep_source_bytes source, int64_t start, int64_t finish) {
 if (source.length != 0 && source.data == NULL) { fputs("PEP_RUNTIME_INVALID_SOURCE_BYTES\n", stderr); exit(1); }
 if (start < 0 || finish < start || (uintmax_t)finish > (uintmax_t)source.length) { fputs("PEP_RUNTIME_BYTE_RANGE\n", stderr); exit(1); }
 if (start != 0 && (uintmax_t)start < (uintmax_t)source.length && (source.data[(size_t)start] & 0xC0) == 0x80) { fputs("PEP_RUNTIME_BYTE_BOUNDARY\n", stderr); exit(1); }
 if ((uintmax_t)finish < (uintmax_t)source.length && (source.data[(size_t)finish] & 0xC0) == 0x80) { fputs("PEP_RUNTIME_BYTE_BOUNDARY\n", stderr); exit(1); }
 size_t pep_slice_len = (size_t)(finish - start); size_t pep_slice_i = 0; while (pep_slice_i < pep_slice_len) {
  unsigned char pep_lead = source.data[(size_t)start + pep_slice_i];
  size_t pep_seq;
  if (pep_lead < 0x80) { pep_seq = 1; }
  else if (pep_lead >= 0xC2 && pep_lead <= 0xDF) { pep_seq = 2; }
  else if (pep_lead >= 0xE0 && pep_lead <= 0xEF) { pep_seq = 3; }
  else if (pep_lead >= 0xF0 && pep_lead <= 0xF4) { pep_seq = 4; }
  else { fputs("PEP_RUNTIME_INVALID_UTF8\n", stderr); exit(1); }
  if (pep_slice_i + pep_seq > pep_slice_len) { fputs("PEP_RUNTIME_INVALID_UTF8\n", stderr); exit(1); }
  if (pep_seq >= 2) { unsigned char pep_second = source.data[(size_t)start + pep_slice_i + 1];
   if ((pep_second & 0xC0) != 0x80) { fputs("PEP_RUNTIME_INVALID_UTF8\n", stderr); exit(1); }
   if (pep_lead == 0xE0 && pep_second < 0xA0) { fputs("PEP_RUNTIME_INVALID_UTF8\n", stderr); exit(1); }
   if (pep_lead == 0xED && pep_second >= 0xA0) { fputs("PEP_RUNTIME_INVALID_UTF8\n", stderr); exit(1); } }
  if (pep_seq >= 3) { if ((source.data[(size_t)start + pep_slice_i + 2] & 0xC0) != 0x80) { fputs("PEP_RUNTIME_INVALID_UTF8\n", stderr); exit(1); } }
  if (pep_seq == 4) { unsigned char pep_second = source.data[(size_t)start + pep_slice_i + 1];
   if ((source.data[(size_t)start + pep_slice_i + 3] & 0xC0) != 0x80) { fputs("PEP_RUNTIME_INVALID_UTF8\n", stderr); exit(1); }
   if (pep_lead == 0xF0 && pep_second < 0x90) { fputs("PEP_RUNTIME_INVALID_UTF8\n", stderr); exit(1); }
   if (pep_lead == 0xF4 && pep_second > 0x8F) { fputs("PEP_RUNTIME_INVALID_UTF8\n", stderr); exit(1); } }
  pep_slice_i = pep_slice_i + pep_seq; }
 if (pep_slice_len > PEP_STR_CONCAT_CAPACITY) { fputs("PEP_RUNTIME_STR_CONCAT_RANGE\n", stderr); exit(1); }
 static unsigned char pep_utf8_slice_pool[PEP_STR_CONCAT_CAPACITY];
 static size_t pep_utf8_slice_used = 0;
 if (pep_slice_len != 0 && pep_utf8_slice_used > PEP_STR_CONCAT_CAPACITY - pep_slice_len) { fputs("PEP_RUNTIME_STR_CONCAT_RANGE\n", stderr); exit(1); }
 unsigned char *pep_slice_out = pep_utf8_slice_pool + pep_utf8_slice_used;
 for (size_t i = 0; i < pep_slice_len; ++i) { pep_slice_out[i] = source.data[(size_t)start + i]; }
 pep_utf8_slice_used += pep_slice_len;
 return (pep_str){ .data = pep_slice_out, .length = pep_slice_len };
}
[[maybe_unused]] static pep_str pep_int_text(int64_t value) {
 unsigned long long pep_mag = (value < 0) ? (unsigned long long)(-(value + 1)) + 1ULL : (unsigned long long)value;
 unsigned char pep_buf[24]; size_t pep_len = 0; _Bool pep_negative = value < 0;
 do { pep_buf[pep_len] = (unsigned char)('0' + (pep_mag % 10ULL)); pep_len = pep_len + 1; pep_mag = pep_mag / 10ULL; } while (pep_mag != 0);
 size_t pep_total = pep_len + (pep_negative ? 1U : 0U);
 if (pep_total > PEP_STR_CONCAT_CAPACITY) { fputs("PEP_RUNTIME_STR_CONCAT_RANGE\n", stderr); exit(1); }
 static unsigned char pep_int_text_pool[PEP_STR_CONCAT_CAPACITY]; static size_t pep_int_text_used = 0;
 if (pep_int_text_used > PEP_STR_CONCAT_CAPACITY - pep_total) { fputs("PEP_RUNTIME_STR_CONCAT_RANGE\n", stderr); exit(1); }
 unsigned char *pep_text_out = pep_int_text_pool + pep_int_text_used;
 if (pep_negative) { *pep_text_out = (unsigned char)'-'; pep_text_out = pep_text_out + 1; }
 while (pep_len != 0) { *pep_text_out = pep_buf[pep_len - 1]; pep_text_out = pep_text_out + 1; pep_len = pep_len - 1; }
 pep_int_text_used += pep_total;
 return (pep_str){ .data = pep_int_text_pool + (pep_int_text_used - pep_total), .length = pep_total };
}
typedef struct { const int64_t *data; size_t length; } pep_list_int;
_Bool pep_contains_int(pep_list_int values, int64_t needle) {
  if (values.length != 0 && values.data == NULL) { fputs("PEP_RUNTIME_INVALID_LIST\n", stderr); exit(1); }
  for (size_t i = 0; i < values.length; ++i) { if (values.data[i] == needle) { return 1; } }
  return 0;
}
typedef struct { const _Bool *data; size_t length; } pep_list_bool;
_Bool pep_contains_bool(pep_list_bool values, _Bool needle) {
  if (values.length != 0 && values.data == NULL) { fputs("PEP_RUNTIME_INVALID_LIST\n", stderr); exit(1); }
  for (size_t i = 0; i < values.length; ++i) { if (values.data[i] == needle) { return 1; } }
  return 0;
}
typedef struct { const pep_str *data; size_t length; } pep_list_str;
[[maybe_unused]] static void pep_say(const unsigned char *value, unsigned long long length) {
  if (length != 0 && value == NULL) { fputs("PEP_RUNTIME_INVALID_STR\n", stderr); exit(1); }
  for (unsigned long long pep_i = 0; pep_i < length; ++pep_i) { fputc((int)value[pep_i], stdout); }
  fputc(10, stdout);
}
int64_t pep_add(int64_t a, int64_t b) {
  if ((b > 0 && a > INT64_MAX - b) || (b < 0 && a < INT64_MIN - b)) { fputs("PEP_RUNTIME_OVERFLOW\n", stderr); exit(1); }
  return a + b;
}
int64_t pep_sub(int64_t a, int64_t b) {
  if ((b < 0 && a > INT64_MAX + b) || (b > 0 && a < INT64_MIN + b)) { fputs("PEP_RUNTIME_OVERFLOW\n", stderr); exit(1); }
  return a - b;
}
int64_t pep_mul(int64_t a, int64_t b) {
  if (a > 0) { if ((b > 0 && a > INT64_MAX / b) || (b < 0 && b < INT64_MIN / a)) { fputs("PEP_RUNTIME_OVERFLOW\n", stderr); exit(1); } }
  else if (a < 0) { if ((b > 0 && a < INT64_MIN / b) || (b < 0 && b < INT64_MAX / a)) { fputs("PEP_RUNTIME_OVERFLOW\n", stderr); exit(1); } }
  return a * b;
}
int64_t pep_div(int64_t a, int64_t b) {
  if (b == 0) { fputs("PEP_RUNTIME_DIVISION_BY_ZERO\n", stderr); exit(1); }
  if (a == INT64_MIN && b == -1) { fputs("PEP_RUNTIME_OVERFLOW\n", stderr); exit(1); }
  return a / b;
}
int64_t pep_neg(int64_t a) {
  if (a == INT64_MIN) { fputs("PEP_RUNTIME_OVERFLOW\n", stderr); exit(1); }
  return -a;
}
[[maybe_unused]] static int64_t pep_checked_length(size_t length) { if ((uintmax_t)length > (uintmax_t)INT64_MAX) { fputs("PEP_RUNTIME_OVERFLOW\n", stderr); exit(1); } return (int64_t)length; }
static int pep_call_depth = 0;
static void pep_enter(void) { if (pep_call_depth >= 512) { fputs("PEP_RUNTIME_CALL_DEPTH\n", stderr); exit(1); } pep_call_depth += 1; }
static void pep_leave(void) { pep_call_depth -= 1; }
[[maybe_unused]] static int64_t pep_invalid_union_tag(void) { fputs("PEP_RUNTIME_INVALID_UNION\n", stderr); exit(1); }
int64_t pep_fn_is_ws(int64_t pep_arg_1);
int64_t pep_fn_is_digit(int64_t pep_arg_1);
int64_t pep_fn_is_ws_at(pep_source_bytes pep_arg_1, int64_t pep_arg_3);
int64_t pep_fn_is_fn2(pep_source_bytes pep_arg_1, int64_t pep_arg_3);
int64_t pep_fn_is_main4(pep_source_bytes pep_arg_1, int64_t pep_arg_3);
int64_t pep_fn_is_int3(pep_source_bytes pep_arg_1, int64_t pep_arg_3);
int64_t pep_fn_is_ret3(pep_source_bytes pep_arg_1, int64_t pep_arg_3);
int64_t pep_fn_is_urn3(pep_source_bytes pep_arg_1, int64_t pep_arg_3);
int64_t pep_fn_is_str3(pep_source_bytes pep_arg_1, int64_t pep_arg_3);
int64_t pep_fn_is_bool4(pep_source_bytes pep_arg_1, int64_t pep_arg_3);
int64_t pep_fn_is_unit4(pep_source_bytes pep_arg_1, int64_t pep_arg_3);
int64_t pep_fn_expect_byte(pep_source_bytes pep_arg_1, int64_t pep_arg_3, int64_t pep_arg_5);
int64_t pep_fn_skip_ws(pep_source_bytes pep_arg_1, int64_t pep_arg_3);
int64_t pep_fn_scan_digits(pep_source_bytes pep_arg_1, int64_t pep_arg_3);
int64_t pep_fn_parse_value(pep_source_bytes pep_arg_1, int64_t pep_arg_3, int64_t pep_arg_5);
int64_t pep_fn_find_fn(pep_source_bytes pep_arg_1);
int64_t pep_fn_find_parens(pep_source_bytes pep_arg_1, int64_t pep_arg_3, int64_t pep_arg_5);
int64_t pep_fn_find_brace(pep_source_bytes pep_arg_1, int64_t pep_arg_3, int64_t pep_arg_5);
int64_t pep_fn_find_ds(pep_source_bytes pep_arg_1, int64_t pep_arg_3, int64_t pep_arg_5);
int64_t pep_fn_check_tail(pep_source_bytes pep_arg_1, int64_t pep_arg_3, int64_t pep_arg_5);
int64_t pep_fn_main(pep_source_bytes pep_arg_1);
int64_t pep_fn_is_ws(int64_t pep_arg_1) {
  pep_enter();
  (void)pep_arg_1;
  int64_t pep_local_4 = 0;
  (void)pep_local_4;
    if (!!(((((pep_arg_1 == 32) || (pep_arg_1 == 9)) || (pep_arg_1 == 10)) || (pep_arg_1 == 13)))) {
      pep_local_4 = 1;
    }
  int64_t pep_result = pep_local_4;
  pep_leave();
  return pep_result;
}
int64_t pep_fn_is_digit(int64_t pep_arg_1) {
  pep_enter();
  (void)pep_arg_1;
  int64_t pep_local_4 = 0;
  (void)pep_local_4;
    if (!!(((48 <= pep_arg_1) && (pep_arg_1 <= 57)))) {
      pep_local_4 = 1;
    }
  int64_t pep_result = pep_local_4;
  pep_leave();
  return pep_result;
}
int64_t pep_fn_is_ws_at(pep_source_bytes pep_arg_1, int64_t pep_arg_3) {
  pep_enter();
  (void)pep_arg_1;
  (void)pep_arg_3;
  int64_t pep_local_6 = 0;
  (void)pep_local_6;
    if (!!(((pep_add(pep_arg_3, 1) <= pep_byte_length(pep_arg_1)) && (pep_fn_is_ws(pep_byte_at(pep_arg_1, pep_arg_3)) == 1)))) {
      pep_local_6 = 1;
    }
  int64_t pep_result = pep_local_6;
  pep_leave();
  return pep_result;
}
int64_t pep_fn_is_fn2(pep_source_bytes pep_arg_1, int64_t pep_arg_3) {
  pep_enter();
  (void)pep_arg_1;
  (void)pep_arg_3;
  int64_t pep_local_6 = 0;
  (void)pep_local_6;
    if (!!((((pep_add(pep_arg_3, 2) <= pep_byte_length(pep_arg_1)) && (pep_byte_at(pep_arg_1, pep_arg_3) == 102)) && (pep_byte_at(pep_arg_1, pep_add(pep_arg_3, 1)) == 110)))) {
      pep_local_6 = 1;
    }
  int64_t pep_result = pep_local_6;
  pep_leave();
  return pep_result;
}
int64_t pep_fn_is_main4(pep_source_bytes pep_arg_1, int64_t pep_arg_3) {
  pep_enter();
  (void)pep_arg_1;
  (void)pep_arg_3;
  int64_t pep_local_6 = 0;
    if (!!((((((pep_add(pep_arg_3, 4) <= pep_byte_length(pep_arg_1)) && (pep_byte_at(pep_arg_1, pep_arg_3) == 109)) && (pep_byte_at(pep_arg_1, pep_add(pep_arg_3, 1)) == 97)) && (pep_byte_at(pep_arg_1, pep_add(pep_arg_3, 2)) == 105)) && (pep_byte_at(pep_arg_1, pep_add(pep_arg_3, 3)) == 110)))) {
      pep_local_6 = 1;
    }
  int64_t pep_result = pep_local_6;
  pep_leave();
  return pep_result;
  (void)pep_local_6;
}
int64_t pep_fn_is_int3(pep_source_bytes pep_arg_1, int64_t pep_arg_3) {
  pep_enter();
  (void)pep_arg_1;
  (void)pep_arg_3;
  int64_t pep_local_6 = 0;
  (void)pep_local_6;
    if (!!(((((pep_add(pep_arg_3, 3) <= pep_byte_length(pep_arg_1)) && (pep_byte_at(pep_arg_1, pep_arg_3) == 73)) && (pep_byte_at(pep_arg_1, pep_add(pep_arg_3, 1)) == 110)) && (pep_byte_at(pep_arg_1, pep_add(pep_arg_3, 2)) == 116)))) {
      pep_local_6 = 1;
    }
  int64_t pep_result = pep_local_6;
  pep_leave();
  return pep_result;
}
int64_t pep_fn_is_ret3(pep_source_bytes pep_arg_1, int64_t pep_arg_3) {
  pep_enter();
  (void)pep_arg_1;
  (void)pep_arg_3;
  int64_t pep_local_6 = 0;
  (void)pep_local_6;
    if (!!(((((pep_add(pep_arg_3, 3) <= pep_byte_length(pep_arg_1)) && (pep_byte_at(pep_arg_1, pep_arg_3) == 114)) && (pep_byte_at(pep_arg_1, pep_add(pep_arg_3, 1)) == 101)) && (pep_byte_at(pep_arg_1, pep_add(pep_arg_3, 2)) == 116)))) {
      pep_local_6 = 1;
    }
  int64_t pep_result = pep_local_6;
  pep_leave();
  return pep_result;
}
int64_t pep_fn_is_urn3(pep_source_bytes pep_arg_1, int64_t pep_arg_3) {
  pep_enter();
  (void)pep_arg_1;
  (void)pep_arg_3;
  int64_t pep_local_6 = 0;
  (void)pep_local_6;
    if (!!(((((pep_add(pep_arg_3, 3) <= pep_byte_length(pep_arg_1)) && (pep_byte_at(pep_arg_1, pep_arg_3) == 117)) && (pep_byte_at(pep_arg_1, pep_add(pep_arg_3, 1)) == 114)) && (pep_byte_at(pep_arg_1, pep_add(pep_arg_3, 2)) == 110)))) {
      pep_local_6 = 1;
    }
  int64_t pep_result = pep_local_6;
  pep_leave();
  return pep_result;
}
int64_t pep_fn_is_str3(pep_source_bytes pep_arg_1, int64_t pep_arg_3) {
  pep_enter();
  (void)pep_arg_1;
  (void)pep_arg_3;
  int64_t pep_local_6 = 0;
  (void)pep_local_6;
    if (!!(((((pep_add(pep_arg_3, 3) <= pep_byte_length(pep_arg_1)) && (pep_byte_at(pep_arg_1, pep_arg_3) == 83)) && (pep_byte_at(pep_arg_1, pep_add(pep_arg_3, 1)) == 116)) && (pep_byte_at(pep_arg_1, pep_add(pep_arg_3, 2)) == 114)))) {
      pep_local_6 = 1;
    }
  int64_t pep_result = pep_local_6;
  pep_leave();
  return pep_result;
}
int64_t pep_fn_is_bool4(pep_source_bytes pep_arg_1, int64_t pep_arg_3) {
  pep_enter();
  (void)pep_arg_1;
  (void)pep_arg_3;
  int64_t pep_local_6 = 0;
    if (!!((((((pep_add(pep_arg_3, 4) <= pep_byte_length(pep_arg_1)) && (pep_byte_at(pep_arg_1, pep_arg_3) == 66)) && (pep_byte_at(pep_arg_1, pep_add(pep_arg_3, 1)) == 111)) && (pep_byte_at(pep_arg_1, pep_add(pep_arg_3, 2)) == 111)) && (pep_byte_at(pep_arg_1, pep_add(pep_arg_3, 3)) == 108)))) {
      pep_local_6 = 1;
    }
  int64_t pep_result = pep_local_6;
  pep_leave();
  return pep_result;
  (void)pep_local_6;
}
int64_t pep_fn_is_unit4(pep_source_bytes pep_arg_1, int64_t pep_arg_3) {
  pep_enter();
  (void)pep_arg_1;
  (void)pep_arg_3;
  int64_t pep_local_6 = 0;
    if (!!((((((pep_add(pep_arg_3, 4) <= pep_byte_length(pep_arg_1)) && (pep_byte_at(pep_arg_1, pep_arg_3) == 85)) && (pep_byte_at(pep_arg_1, pep_add(pep_arg_3, 1)) == 110)) && (pep_byte_at(pep_arg_1, pep_add(pep_arg_3, 2)) == 105)) && (pep_byte_at(pep_arg_1, pep_add(pep_arg_3, 3)) == 116)))) {
      pep_local_6 = 1;
    }
  int64_t pep_result = pep_local_6;
  pep_leave();
  return pep_result;
  (void)pep_local_6;
}
int64_t pep_fn_expect_byte(pep_source_bytes pep_arg_1, int64_t pep_arg_3, int64_t pep_arg_5) {
  pep_enter();
  (void)pep_arg_1;
  (void)pep_arg_3;
  (void)pep_arg_5;
  int64_t pep_local_8 = 0;
  (void)pep_local_8;
    if (!!(((pep_add(pep_arg_3, 1) <= pep_byte_length(pep_arg_1)) && (pep_byte_at(pep_arg_1, pep_arg_3) == pep_arg_5)))) {
      pep_local_8 = 1;
    }
  int64_t pep_result = pep_local_8;
  pep_leave();
  return pep_result;
}
int64_t pep_fn_skip_ws(pep_source_bytes pep_arg_1, int64_t pep_arg_3) {
  pep_enter();
  (void)pep_arg_1;
  (void)pep_arg_3;
  int64_t pep_local_6 = pep_arg_3;
  int64_t pep_local_8 = pep_byte_length(pep_arg_1);
  int64_t pep_local_11 = pep_arg_3;
  int64_t pep_local_13 = 0;
  while (!!((pep_add(pep_local_6, 1) <= pep_local_8))) {
    if (!!((pep_fn_is_ws(pep_byte_at(pep_arg_1, pep_local_6)) == 1))) {
      pep_local_6 = pep_add(pep_local_6, 1);
    } else {
      pep_local_11 = pep_local_6;
      pep_local_13 = 1;
      pep_local_6 = pep_local_8;
    }
  }
  int64_t pep_local_38 = pep_local_8;
    if (!!((pep_local_13 == 1))) {
      pep_local_38 = pep_local_11;
    }
  int64_t pep_result = pep_local_38;
  pep_leave();
  return pep_result;
  (void)pep_local_6;
  (void)pep_local_8;
  (void)pep_local_11;
  (void)pep_local_13;
  (void)pep_local_38;
}
int64_t pep_fn_scan_digits(pep_source_bytes pep_arg_1, int64_t pep_arg_3) {
  pep_enter();
  (void)pep_arg_1;
  (void)pep_arg_3;
  int64_t pep_local_6 = pep_arg_3;
  int64_t pep_local_8 = pep_byte_length(pep_arg_1);
  int64_t pep_local_11 = pep_arg_3;
  int64_t pep_local_13 = 0;
  while (!!((pep_add(pep_local_6, 1) <= pep_local_8))) {
    if (!!((pep_fn_is_digit(pep_byte_at(pep_arg_1, pep_local_6)) == 1))) {
      pep_local_6 = pep_add(pep_local_6, 1);
    } else {
      pep_local_11 = pep_local_6;
      pep_local_13 = 1;
      pep_local_6 = pep_local_8;
    }
  }
  int64_t pep_local_38 = pep_local_8;
    if (!!((pep_local_13 == 1))) {
      pep_local_38 = pep_local_11;
    }
  int64_t pep_result = pep_local_38;
  pep_leave();
  return pep_result;
  (void)pep_local_6;
  (void)pep_local_8;
  (void)pep_local_11;
  (void)pep_local_13;
  (void)pep_local_38;
}
int64_t pep_fn_parse_value(pep_source_bytes pep_arg_1, int64_t pep_arg_3, int64_t pep_arg_5) {
  pep_enter();
  (void)pep_arg_1;
  (void)pep_arg_3;
  (void)pep_arg_5;
  int64_t pep_local_8 = 0;
  (void)pep_local_8;
  int64_t pep_local_10 = pep_arg_3;
  (void)pep_local_10;
  while (!!((pep_add(pep_local_10, 1) <= pep_arg_5))) {
    pep_local_8 = pep_add(pep_mul(pep_local_8, 10), pep_sub(pep_byte_at(pep_arg_1, pep_local_10), 48));
    pep_local_10 = pep_add(pep_local_10, 1);
  }
  int64_t pep_result = pep_local_8;
  pep_leave();
  return pep_result;
}
int64_t pep_fn_find_fn(pep_source_bytes pep_arg_1) {
  pep_enter();
  (void)pep_arg_1;
  int64_t pep_local_4 = 0;
  int64_t pep_local_6 = pep_fn_skip_ws(pep_arg_1, 0);
  int64_t pep_local_10 = pep_sub(pep_byte_length(pep_arg_1), pep_local_6);
    if (!!((pep_local_10 <= 0))) {
      pep_local_4 = 6;
    }
    if (!!(((pep_local_4 == 0) && (pep_fn_is_fn2(pep_arg_1, pep_local_6) == 0)))) {
      pep_local_4 = 1;
    }
    if (!!((pep_local_4 == 0))) {
      pep_local_6 = pep_add(pep_local_6, 2);
    }
    if (!!(((pep_local_4 == 0) && (pep_fn_is_ws_at(pep_arg_1, pep_local_6) == 0)))) {
      pep_local_4 = 1;
    }
    if (!!((pep_local_4 == 0))) {
      pep_local_6 = pep_fn_skip_ws(pep_arg_1, pep_local_6);
    }
    if (!!(((pep_local_4 == 0) && (pep_fn_is_main4(pep_arg_1, pep_local_6) == 0)))) {
      pep_local_4 = 1;
    }
    if (!!((pep_local_4 == 0))) {
      pep_local_6 = pep_add(pep_local_6, 4);
    }
  int64_t pep_local_81 = pep_sub(0, 1);
    if (!!((pep_local_4 == 0))) {
      pep_local_81 = pep_local_6;
    }
    if (!!((pep_local_4 == 6))) {
      pep_local_81 = pep_sub(0, 6);
    }
  int64_t pep_result = pep_local_81;
  pep_leave();
  return pep_result;
  (void)pep_local_4;
  (void)pep_local_6;
  (void)pep_local_10;
  (void)pep_local_81;
}
int64_t pep_fn_find_parens(pep_source_bytes pep_arg_1, int64_t pep_arg_3, int64_t pep_arg_5) {
  pep_enter();
  (void)pep_arg_1;
  (void)pep_arg_3;
  (void)pep_arg_5;
  int64_t pep_local_8 = pep_sub(0, 1);
  int64_t pep_local_12 = pep_arg_3;
  int64_t pep_local_14 = pep_arg_5;
    if (!!((pep_local_14 == 0))) {
      pep_local_12 = pep_fn_skip_ws(pep_arg_1, pep_local_12);
    }
    if (!!(((pep_local_14 == 0) && (pep_fn_expect_byte(pep_arg_1, pep_local_12, 40) == 0)))) {
      pep_local_14 = 1;
    }
    if (!!((pep_local_14 == 0))) {
      pep_local_12 = pep_add(pep_local_12, 1);
    }
    if (!!((pep_local_14 == 0))) {
      pep_local_12 = pep_fn_skip_ws(pep_arg_1, pep_local_12);
    }
    if (!!(((pep_local_14 == 0) && (pep_fn_expect_byte(pep_arg_1, pep_local_12, 41) == 0)))) {
      pep_local_14 = 1;
    }
    if (!!((pep_local_14 == 0))) {
      pep_local_12 = pep_add(pep_local_12, 1);
    }
    if (!!((pep_local_14 == 0))) {
      pep_local_8 = pep_local_12;
    }
  int64_t pep_result = pep_local_8;
  pep_leave();
  return pep_result;
  (void)pep_local_8;
  (void)pep_local_12;
  (void)pep_local_14;
}
int64_t pep_fn_find_brace(pep_source_bytes pep_arg_1, int64_t pep_arg_3, int64_t pep_arg_5) {
  pep_enter();
  (void)pep_arg_1;
  (void)pep_arg_3;
  (void)pep_arg_5;
  int64_t pep_local_8 = pep_sub(0, 1);
  int64_t pep_local_12 = pep_arg_3;
  int64_t pep_local_14 = pep_arg_5;
  int64_t pep_local_16 = pep_arg_5;
    if (!!((pep_local_14 == 0))) {
      pep_local_12 = pep_fn_skip_ws(pep_arg_1, pep_local_12);
    }
    if (!!(((pep_local_14 == 0) && (pep_fn_expect_byte(pep_arg_1, pep_local_12, 45) == 0)))) {
      pep_local_14 = 1;
    }
    if (!!((pep_local_14 == 0))) {
      pep_local_12 = pep_add(pep_local_12, 1);
    }
    if (!!(((pep_local_14 == 0) && (pep_fn_expect_byte(pep_arg_1, pep_local_12, 62) == 0)))) {
      pep_local_14 = 1;
    }
    if (!!((pep_local_14 == 0))) {
      pep_local_12 = pep_add(pep_local_12, 1);
    }
    if (!!((pep_local_14 == 0))) {
      pep_local_12 = pep_fn_skip_ws(pep_arg_1, pep_local_12);
    }
    if (!!(((pep_local_14 == 0) && (pep_fn_is_int3(pep_arg_1, pep_local_12) == 0)))) {
      pep_local_14 = 1;
    }
    if (!!((((pep_local_16 == 0) && (pep_local_14 == 1)) && (pep_fn_is_str3(pep_arg_1, pep_local_12) == 1)))) {
      pep_local_14 = 5;
    }
    if (!!((((pep_local_16 == 0) && (pep_local_14 == 1)) && (pep_fn_is_bool4(pep_arg_1, pep_local_12) == 1)))) {
      pep_local_14 = 5;
    }
    if (!!((((pep_local_16 == 0) && (pep_local_14 == 1)) && (pep_fn_is_unit4(pep_arg_1, pep_local_12) == 1)))) {
      pep_local_14 = 5;
    }
  int64_t pep_local_136 = (((pep_local_16 == 0) && (pep_local_14 == 5)) && (pep_fn_is_str3(pep_arg_1, pep_local_12) == 1));
    if (!!(((pep_local_136 && (pep_fn_is_ws_at(pep_arg_1, pep_add(pep_local_12, 3)) == 0)) && (pep_fn_expect_byte(pep_arg_1, pep_add(pep_local_12, 3), 123) == 0)))) {
      pep_local_14 = 1;
    }
  int64_t pep_local_171 = (((pep_local_16 == 0) && (pep_local_14 == 5)) && (pep_fn_is_bool4(pep_arg_1, pep_local_12) == 1));
    if (!!(((pep_local_171 && (pep_fn_is_ws_at(pep_arg_1, pep_add(pep_local_12, 4)) == 0)) && (pep_fn_expect_byte(pep_arg_1, pep_add(pep_local_12, 4), 123) == 0)))) {
      pep_local_14 = 1;
    }
  int64_t pep_local_206 = (((pep_local_16 == 0) && (pep_local_14 == 5)) && (pep_fn_is_unit4(pep_arg_1, pep_local_12) == 1));
    if (!!(((pep_local_206 && (pep_fn_is_ws_at(pep_arg_1, pep_add(pep_local_12, 4)) == 0)) && (pep_fn_expect_byte(pep_arg_1, pep_add(pep_local_12, 4), 123) == 0)))) {
      pep_local_14 = 1;
    }
    if (!!((pep_local_14 == 0))) {
      pep_local_12 = pep_add(pep_local_12, 3);
    }
    if (!!((pep_local_14 == 0))) {
      pep_local_12 = pep_fn_skip_ws(pep_arg_1, pep_local_12);
    }
    if (!!(((pep_local_14 == 0) && (pep_fn_expect_byte(pep_arg_1, pep_local_12, 123) == 0)))) {
      pep_local_14 = 1;
    }
    if (!!((pep_local_14 == 0))) {
      pep_local_12 = pep_add(pep_local_12, 1);
    }
    if (!!((pep_local_14 == 0))) {
      pep_local_8 = pep_local_12;
    }
    if (!!((pep_local_14 == 5))) {
      pep_local_8 = pep_sub(0, 5);
    }
  int64_t pep_result = pep_local_8;
  pep_leave();
  return pep_result;
  (void)pep_local_8;
  (void)pep_local_12;
  (void)pep_local_14;
  (void)pep_local_16;
  (void)pep_local_136;
  (void)pep_local_171;
  (void)pep_local_206;
}
int64_t pep_fn_find_ds(pep_source_bytes pep_arg_1, int64_t pep_arg_3, int64_t pep_arg_5) {
  pep_enter();
  (void)pep_arg_1;
  (void)pep_arg_3;
  (void)pep_arg_5;
  int64_t pep_local_8 = pep_sub(0, 1);
  int64_t pep_local_12 = pep_arg_3;
  int64_t pep_local_14 = pep_arg_5;
    if (!!((pep_local_14 == 0))) {
      pep_local_12 = pep_fn_skip_ws(pep_arg_1, pep_local_12);
    }
    if (!!(((pep_local_14 == 0) && (pep_fn_is_ret3(pep_arg_1, pep_local_12) == 0)))) {
      pep_local_14 = 1;
    }
    if (!!(((pep_local_14 == 0) && (pep_fn_is_urn3(pep_arg_1, pep_add(pep_local_12, 3)) == 0)))) {
      pep_local_14 = 1;
    }
    if (!!((pep_local_14 == 0))) {
      pep_local_12 = pep_add(pep_local_12, 6);
    }
    if (!!(((pep_local_14 == 0) && (pep_fn_is_ws_at(pep_arg_1, pep_local_12) == 0)))) {
      pep_local_14 = 2;
    }
    if (!!((pep_local_14 == 0))) {
      pep_local_12 = pep_fn_skip_ws(pep_arg_1, pep_local_12);
    }
  int64_t pep_local_78 = pep_sub(0, 1);
  int64_t pep_local_82 = pep_sub(0, 1);
    if (!!((pep_local_14 == 0))) {
      pep_local_78 = pep_local_12;
      pep_local_82 = pep_fn_scan_digits(pep_arg_1, pep_local_12);
    }
    if (!!(((pep_local_14 == 0) && (pep_local_82 == pep_local_78)))) {
      pep_local_14 = 2;
    }
    if (!!((pep_local_14 == 0))) {
      pep_local_8 = pep_local_78;
    }
    if (!!((pep_local_14 == 2))) {
      pep_local_8 = pep_sub(0, 2);
    }
  int64_t pep_result = pep_local_8;
  pep_leave();
  return pep_result;
  (void)pep_local_8;
  (void)pep_local_12;
  (void)pep_local_14;
  (void)pep_local_78;
  (void)pep_local_82;
}
int64_t pep_fn_check_tail(pep_source_bytes pep_arg_1, int64_t pep_arg_3, int64_t pep_arg_5) {
  pep_enter();
  (void)pep_arg_1;
  (void)pep_arg_3;
  (void)pep_arg_5;
  int64_t pep_local_8 = pep_arg_5;
  int64_t pep_local_10 = pep_arg_3;
    if (!!((pep_arg_5 == 0))) {
      pep_local_10 = pep_fn_skip_ws(pep_arg_1, pep_local_10);
    }
    if (!!(((pep_arg_5 == 0) && (pep_fn_expect_byte(pep_arg_1, pep_local_10, 125) == 0)))) {
      pep_local_8 = 1;
    }
    if (!!((pep_arg_5 == 0))) {
      pep_local_10 = pep_add(pep_local_10, 1);
    }
    if (!!((pep_arg_5 == 0))) {
      pep_local_10 = pep_fn_skip_ws(pep_arg_1, pep_local_10);
    }
  int64_t pep_local_49 = pep_sub(pep_byte_length(pep_arg_1), pep_local_10);
    if (!!(((pep_arg_5 == 0) && (1 <= pep_local_49)))) {
      pep_local_8 = 3;
    }
  int64_t pep_result = pep_local_8;
  pep_leave();
  return pep_result;
  (void)pep_local_8;
  (void)pep_local_10;
  (void)pep_local_49;
}
int64_t pep_fn_main(pep_source_bytes pep_arg_1) {
  pep_enter();
  (void)pep_arg_1;
  int64_t pep_local_4 = 0;
  int64_t pep_local_6 = pep_sub(0, 1);
  int64_t pep_local_10 = pep_sub(0, 2);
  int64_t pep_local_14 = pep_sub(0, 5);
  int64_t pep_local_18 = pep_sub(0, 6);
  int64_t pep_local_22 = pep_fn_find_fn(pep_arg_1);
    if (!!((pep_local_22 == pep_local_6))) {
      pep_local_4 = 1;
    }
    if (!!((pep_local_22 == pep_local_18))) {
      pep_local_4 = 6;
    }
  int64_t pep_local_37 = pep_fn_find_parens(pep_arg_1, pep_local_22, pep_local_4);
    if (!!(((pep_local_4 == 0) && (pep_local_37 == pep_local_6)))) {
      pep_local_4 = 1;
    }
  int64_t pep_local_52 = pep_fn_find_brace(pep_arg_1, pep_local_37, pep_local_4);
    if (!!(((pep_local_4 == 0) && (pep_local_52 == pep_local_6)))) {
      pep_local_4 = 1;
    }
    if (!!((pep_local_52 == pep_local_14))) {
      pep_local_4 = 5;
    }
  int64_t pep_local_73 = pep_fn_find_ds(pep_arg_1, pep_local_52, pep_local_4);
    if (!!(((pep_local_4 == 0) && (pep_local_73 == pep_local_6)))) {
      pep_local_4 = 1;
    }
    if (!!(((pep_local_4 == 0) && (pep_local_73 == pep_local_10)))) {
      pep_local_4 = 2;
    }
  int64_t pep_local_98 = 0;
    if (!!((pep_local_4 == 0))) {
      pep_local_98 = pep_fn_scan_digits(pep_arg_1, pep_local_73);
    }
    if (!!(((pep_local_4 == 0) && (19 <= pep_sub(pep_local_98, pep_local_73))))) {
      pep_local_4 = 4;
    }
  int64_t pep_local_120 = 0;
    if (!!((pep_local_4 == 0))) {
      pep_local_120 = pep_fn_parse_value(pep_arg_1, pep_local_73, pep_local_98);
    }
  int64_t pep_local_131 = pep_fn_check_tail(pep_arg_1, pep_local_98, pep_local_4);
    if (!!((pep_local_4 == 0))) {
      pep_local_4 = pep_local_131;
    }
    if (!!((pep_local_4 == 0))) {
  pep_say((pep_str){ .data = (const unsigned char *)"int main", .length = 8 }.data, (pep_str){ .data = (const unsigned char *)"int main", .length = 8 }.length);
  pep_say((pep_str){ .data = (const unsigned char *)"(", .length = 1 }.data, (pep_str){ .data = (const unsigned char *)"(", .length = 1 }.length);
  pep_say((pep_str){ .data = (const unsigned char *)"void", .length = 4 }.data, (pep_str){ .data = (const unsigned char *)"void", .length = 4 }.length);
  pep_say((pep_str){ .data = (const unsigned char *)")", .length = 1 }.data, (pep_str){ .data = (const unsigned char *)")", .length = 1 }.length);
  pep_say((pep_str){ .data = (const unsigned char *)"{", .length = 1 }.data, (pep_str){ .data = (const unsigned char *)"{", .length = 1 }.length);
  pep_say((pep_str){ .data = (const unsigned char *)"return", .length = 6 }.data, (pep_str){ .data = (const unsigned char *)"return", .length = 6 }.length);
  pep_say(pep_int_text(pep_local_120).data, pep_int_text(pep_local_120).length);
  pep_say((pep_str){ .data = (const unsigned char *)";", .length = 1 }.data, (pep_str){ .data = (const unsigned char *)";", .length = 1 }.length);
  pep_say((pep_str){ .data = (const unsigned char *)"}", .length = 1 }.data, (pep_str){ .data = (const unsigned char *)"}", .length = 1 }.length);
    }
    if (!!((pep_local_4 == 1))) {
  pep_say((pep_str){ .data = (const unsigned char *)"ERR shape", .length = 9 }.data, (pep_str){ .data = (const unsigned char *)"ERR shape", .length = 9 }.length);
    }
    if (!!((pep_local_4 == 2))) {
  pep_say((pep_str){ .data = (const unsigned char *)"ERR literal", .length = 11 }.data, (pep_str){ .data = (const unsigned char *)"ERR literal", .length = 11 }.length);
    }
    if (!!((pep_local_4 == 3))) {
  pep_say((pep_str){ .data = (const unsigned char *)"ERR junk", .length = 8 }.data, (pep_str){ .data = (const unsigned char *)"ERR junk", .length = 8 }.length);
    }
    if (!!((pep_local_4 == 4))) {
  pep_say((pep_str){ .data = (const unsigned char *)"ERR longlit", .length = 11 }.data, (pep_str){ .data = (const unsigned char *)"ERR longlit", .length = 11 }.length);
    }
    if (!!((pep_local_4 == 5))) {
  pep_say((pep_str){ .data = (const unsigned char *)"ERR unsupported", .length = 15 }.data, (pep_str){ .data = (const unsigned char *)"ERR unsupported", .length = 15 }.length);
    }
    if (!!((pep_local_4 == 6))) {
      pep_local_4 = 0;
    }
  int64_t pep_result = pep_local_4;
  pep_leave();
  return pep_result;
  (void)pep_local_4;
  (void)pep_local_6;
  (void)pep_local_10;
  (void)pep_local_14;
  (void)pep_local_18;
  (void)pep_local_22;
  (void)pep_local_37;
  (void)pep_local_52;
  (void)pep_local_73;
  (void)pep_local_98;
  (void)pep_local_120;
  (void)pep_local_131;
}
int main(int argc, char **argv) {
  if (argc < 2) { fputs("PEP_RUNTIME_SOURCE_CONTEXT\n", stderr); return 1; }
#if defined(_MSC_VER)
#pragma warning(push)
#pragma warning(disable: 4996)
#endif
  FILE *pep_source_file = fopen(argv[1], "rb");
  if (pep_source_file == NULL) { fputs("PEP_RUNTIME_SOURCE_OPEN\n", stderr); return 1; }
  if (fseek(pep_source_file, 0, SEEK_END) != 0) { fputs("PEP_RUNTIME_SOURCE_OPEN\n", stderr); return 1; }
  long pep_source_length = ftell(pep_source_file);
  if (pep_source_length < 0) { fputs("PEP_RUNTIME_SOURCE_OPEN\n", stderr); return 1; }
  if (fseek(pep_source_file, 0, SEEK_SET) != 0) { fputs("PEP_RUNTIME_SOURCE_OPEN\n", stderr); return 1; }
  unsigned char *pep_source_data = (unsigned char *)malloc((size_t)pep_source_length + 1u);
  if (pep_source_data == NULL) { fputs("PEP_RUNTIME_SOURCE_OPEN\n", stderr); return 1; }
  if (pep_source_length > 0 && fread(pep_source_data, 1, (size_t)pep_source_length, pep_source_file) != (size_t)pep_source_length) { fputs("PEP_RUNTIME_SOURCE_OPEN\n", stderr); return 1; }
  (void)fclose(pep_source_file);
#if defined(_MSC_VER)
#pragma warning(pop)
#endif
  long long pep_rc = (long long)(pep_fn_main((pep_source_bytes){ .data = pep_source_data, .length = (size_t)pep_source_length }));
  free(pep_source_data);
  return (int)pep_rc;
}
