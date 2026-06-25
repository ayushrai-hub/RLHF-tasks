# NPY format

All numeric array outputs use the NumPy NPY format, version 1.0. This makes
the artifacts trivial to load from Python with `numpy.load`.

NPY v1.0 layout:

    bytes 0-5    magic "\x93NUMPY"
    byte  6      major version (1)
    byte  7      minor version (0)
    bytes 8-9    little-endian uint16 header_len
    bytes 10..   ASCII header dict (length = header_len), padded with spaces
                 and terminated by a single newline so the total prefix length
                 (10 + header_len) is a multiple of 64

The header dict has three keys: `descr`, `fortran_order`, `shape`. Example:

    {'descr': '<f4', 'fortran_order': False, 'shape': (200, 100), }

Write all arrays as little-endian float32 (`<f4`) in C order
(`fortran_order: False`). Use row-major flattening: for a 2D array with shape
`(nz, nx)`, element `(iz, ix)` is at offset `iz * nx + ix`.

The header line must end with `\n` and the total prefix length must align to
64 bytes — pad with ASCII spaces between the closing `}` and the trailing
newline.
