# atlas JSON schema

File: /app/output/wcs-atlas.json

Fields:

- version: integer 1
- fits_path: string path used for ingest
- naxis1, naxis2: image dimensions from header (0 when NAXIS is 0)
- ctype1, ctype2: projection type strings from header
- projection: TAN or SIN derived from CTYPE
- crpix1, crpix2: reference pixel (1-based FITS)
- crval1, crval2: reference sky coordinates in degrees
- pixel_scale_arcsec: mean absolute diagonal scale in arcseconds per pixel
- corners: array of four objects with pixel_x, pixel_y, ra_deg, dec_deg sorted by ra_deg ascending then dec_deg
- axis_midpoints: array of four objects for center of left, right, bottom, and top edges
- fingerprint: lowercase hex digest of canonical keyword string

Corner pixels are (1,1), (naxis1,1), (1,naxis2), (naxis1,naxis2). When naxis is 0 use (1,1) for all corners.
