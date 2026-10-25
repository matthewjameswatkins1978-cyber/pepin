#include "pep_runtime.h"
extern void *GetStdHandle(int); extern int WriteFile(void *, const void *, unsigned long, unsigned long *, void *);

void pep_say(const unsigned char *value, unsigned long long length) { void *handle = GetStdHandle(-11); unsigned long written;
  if (length != 0) {
    for (unsigned long long index = 0; index < length; ++index) (void)WriteFile(handle, &value[index], 1, &written, 0);
  }
  { unsigned char newline = 10; (void)WriteFile(handle, &newline, 1, &written, 0); }
}
