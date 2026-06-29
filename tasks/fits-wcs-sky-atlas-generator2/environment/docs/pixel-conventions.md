# pixel conventions

FITS pixel coordinates are 1-based inclusive.

CRPIX1 and CRPIX2 refer to the pixel center of the reference pixel.

Image corners for NAXIS1 = N, NAXIS2 = M:

(1, 1), (N, 1), (1, M), (N, M)

When NAXIS is 0 or keywords missing, treat N and M as 1 for corner evaluation.

Axis midpoints: (1, (M+1)/2), (N, (M+1)/2), ((N+1)/2, 1), ((N+1)/2, M) using floating midpoints when dimensions are even.
