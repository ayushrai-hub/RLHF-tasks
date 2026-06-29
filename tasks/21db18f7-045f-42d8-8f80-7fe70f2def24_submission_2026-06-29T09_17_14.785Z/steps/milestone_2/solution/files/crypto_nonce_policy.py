"""Nonce generation policy for AES-GCM field encryption."""

import os

from config import AES_GCM_NONCE_LENGTH


def next_nonce() -> bytes:
    return os.urandom(AES_GCM_NONCE_LENGTH)
