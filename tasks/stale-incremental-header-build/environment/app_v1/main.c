#include <stdio.h>
#include <string.h>

#include "../libcore/widget.h"

int main(void) {
  const char *lab = widget_cap_label();
  fputs("@CAP:", stdout);
  fputs(lab, stdout);
  fputc('\n', stdout);
  return 0;
}
