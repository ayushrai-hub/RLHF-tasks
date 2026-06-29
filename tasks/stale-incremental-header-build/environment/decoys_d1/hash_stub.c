unsigned int hash_stub_fold(const unsigned char *p, int n) {
  unsigned int h = 2166136261u;
  for (int i = 0; i < n; i++) {
    h ^= p[i];
    h *= 16777619u;
  }
  return h;
}
