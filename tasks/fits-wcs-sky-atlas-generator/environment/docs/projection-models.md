# projection models

CTYPE1 and CTYPE2 suffix after the fourth character selects projection (e.g. RA---TAN gives TAN).

TAN (gnomonic) with xi and eta in degrees before radians conversion:

Let ra0 = CRVAL1, dec0 = CRVAL2 in radians, xi_r = radians(xi), eta_r = radians(eta).

ra = ra0 + atan2(xi_r, cos(dec0) - eta_r * sin(dec0))
dec = atan2(sin(dec0) + eta_r * cos(dec0), sqrt(xi_r*xi_r + (cos(dec0) - eta_r*sin(dec0))^2))

Return ra and dec in degrees normalized to [0, 360) for RA.

SIN (orthographic sine):

rho = sqrt(xi_r*xi_r + eta_r*eta_r)
if rho is zero, return CRVAL.

cos_r = cos(rho)
sin_r = sin(rho)
dec = asin(sin(dec0)*cos_r + (eta_r/rho)*cos(dec0)*sin_r)  [when rho > 0]
ra = ra0 + atan2(xi_r*sin_r, rho*cos(dec0)*cos_r - eta_r*sin(dec0)*sin_r)

Use the SIN branch only when projection is SIN.
