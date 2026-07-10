"""Helpers for local fixture maintenance; the analyzer itself is implemented in Go."""

import base64
import gzip
import hashlib
import sqlite3
import struct
import zipfile


FORMAT_MODULES = (base64, gzip, hashlib, sqlite3, struct, zipfile)
