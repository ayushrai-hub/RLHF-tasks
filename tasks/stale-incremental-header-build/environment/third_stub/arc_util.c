int arc_util_align(int x, int a) {
  if (a <= 0) {
    return x;
  }
  int m = x % a;
  return m ? x + (a - m) : x;
}
