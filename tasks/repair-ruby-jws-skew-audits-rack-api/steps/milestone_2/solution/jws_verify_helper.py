#!/usr/bin/env python3
"""Oracle-only detached JWS signature verification helper for the reference solver."""
from __future__ import annotations

import base64
import json
import sys

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature


def b64url_decode(data: str) -> bytes:
    pad = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + pad)


def jwk_to_public_key(jwk: dict):
    alg = jwk["alg"]
    if alg == "RS256":
        n = int.from_bytes(b64url_decode(jwk["n"]), "big")
        e = int.from_bytes(b64url_decode(jwk["e"]), "big")
        return rsa.RSAPublicNumbers(e, n).public_key()
    if alg == "ES256":
        x = b64url_decode(jwk["x"])
        y = b64url_decode(jwk["y"])
        return ec.EllipticCurvePublicNumbers(
            int.from_bytes(x, "big"),
            int.from_bytes(y, "big"),
            ec.SECP256R1(),
        ).public_key()
    if alg == "EdDSA":
        return ed25519.Ed25519PublicKey.from_public_bytes(b64url_decode(jwk["x"]))
    raise ValueError(f"unsupported alg {alg}")


def verify_signature(alg: str, header_b64: str, payload_b64: str, sig_b64: str, jwk: dict) -> bool:
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = b64url_decode(sig_b64)
    key = jwk_to_public_key(jwk)
    try:
        if alg == "RS256":
            key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
            return True
        if alg == "ES256":
            if len(signature) == 64:
                r = int.from_bytes(signature[:32], "big")
                s = int.from_bytes(signature[32:], "big")
                der_sig = encode_dss_signature(r, s)
            else:
                der_sig = signature
            key.verify(der_sig, signing_input, ec.ECDSA(hashes.SHA256()))
            return True
        if alg == "EdDSA":
            key.verify(signature, signing_input)
            return True
    except Exception:
        return False
    return False


def main() -> None:
    doc = json.load(sys.stdin)
    ok = verify_signature(
        doc["alg"],
        doc["header_b64"],
        doc["payload_b64"],
        doc["sig_b64"],
        doc["jwk"],
    )
    print("ok" if ok else "fail")


if __name__ == "__main__":
    main()
