# WCS linear transform

Given 1-based pixel (x, y), intermediate coordinates in degrees:

dx = x - CRPIX1
dy = y - CRPIX2

If CD1_1 is present, linear part is:

xi = CD1_1 * dx + CD1_2 * dy
eta = CD2_1 * dx + CD2_2 * dy

If PC and CDELT are present without CD, compose:

m_ij = PC_i_j * CDELT_j   (j indexes column, CDELT_1 applies to first index)

xi = m_11 * dx + m_12 * dy
eta = m_21 * dx + m_22 * dy

CD matrix takes precedence when any CD_i_j keyword is present.
