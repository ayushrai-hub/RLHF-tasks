#include "wcs_atlas/flux_decoy.h"

namespace wcs {

double integrated_flux_stub(const double* pixels, int n) {
  double sum = 0.0;
  for (int i = 0; i < n; ++i) {
    sum += pixels[i];
  }
  return sum;
}

}  // namespace wcs
