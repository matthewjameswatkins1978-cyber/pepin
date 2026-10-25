#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "moonbit.h"

static int source_error = 0;

moonbit_bytes_t pep_read_stdin(void) {
  size_t capacity = 4096;
  size_t length = 0;
  unsigned char *buffer = (unsigned char *)malloc(capacity);
  if (buffer == NULL) {
    source_error = 1;
    return moonbit_make_bytes(0, 0);
  }
  for (;;) {
    int ch = getchar();
    if (ch == EOF) {
      if (ferror(stdin)) source_error = 2;
      break;
    }
    if (length == 67108864u) {
      source_error = 3;
      break;
    }
    if (length == capacity) {
      size_t next = capacity * 2;
      unsigned char *grown = (unsigned char *)realloc(buffer, next);
      if (grown == NULL) {
        source_error = 1;
        break;
      }
      buffer = grown;
      capacity = next;
    }
    buffer[length++] = (unsigned char)ch;
  }
  moonbit_bytes_t result = moonbit_make_bytes_raw((int32_t)length);
  if (length != 0) memcpy(result, buffer, length);
  free(buffer);
  return result;
}

int32_t pep_stdin_error(void) {
  return source_error;
}
