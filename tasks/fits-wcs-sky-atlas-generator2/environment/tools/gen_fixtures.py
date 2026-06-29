#!/usr/bin/env python3
"""Generate FITS header fixtures for wcs-atlas verifier."""

from __future__ import annotations

from pathlib import Path

BLOCK = 2880
CARD_LEN = 80


def _card(keyword: str, value: str | int | float | bool, comment: str = "") -> str:
    kw = keyword.upper()[:8].ljust(8)
    if isinstance(value, bool):
        val = "T" if value else "F"
        body = f"{kw}= {val!s:>20}"
    elif isinstance(value, str):
        s = value
        if not (s.startswith("'") and s.endswith("'")):
            s = f"'{s}'"
        body = f"{kw}= {s}"
    elif isinstance(value, float):
        body = f"{kw}= {value:>20G}"
    else:
        body = f"{kw}= {value:>20d}"
    if comment:
        if len(body) < 30:
            body = body.ljust(30) + f"/ {comment}"
        else:
            body = body[:30] + f"/ {comment}"
    return body.ljust(CARD_LEN)


def write_fits(path: Path, cards: list[str], data: bytes = b"") -> None:
    lines = list(cards)
    lines.append(_card("END", ""))
    text = "".join(lines)
    pad = (BLOCK - (len(text) % BLOCK)) % BLOCK
    text += " " * pad
    if data:
        rem = len(data) % BLOCK
        if rem:
            data += b"\x00" * (BLOCK - rem)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("ascii") + data)


def tan_basic_cards() -> list[str]:
    return [
        _card("SIMPLE", True, "conforms to FITS"),
        _card("BITPIX", 8),
        _card("NAXIS", 2),
        _card("NAXIS1", 200),
        _card("NAXIS2", 100),
        _card("CTYPE1", "RA---TAN"),
        _card("CTYPE2", "DEC--TAN"),
        _card("CRPIX1", 100.5),
        _card("CRPIX2", 50.5),
        _card("CRVAL1", 45.0),
        _card("CRVAL2", 30.0),
        _card("CDELT1", -0.02),
        _card("CDELT2", 0.02),
    ]


def sin_basic_cards() -> list[str]:
    c = tan_basic_cards()
    c[5] = _card("CTYPE1", "RA---SIN")
    c[6] = _card("CTYPE2", "DEC--SIN")
    c[9] = _card("CRVAL1", 120.0)
    c[10] = _card("CRVAL2", -20.0)
    return c


def pc_skew_cards() -> list[str]:
    return [
        _card("SIMPLE", True),
        _card("BITPIX", 8),
        _card("NAXIS", 2),
        _card("NAXIS1", 64),
        _card("NAXIS2", 64),
        _card("CTYPE1", "RA---TAN"),
        _card("CTYPE2", "DEC--TAN"),
        _card("CRPIX1", 32.0),
        _card("CRPIX2", 32.0),
        _card("CRVAL1", 10.0),
        _card("CRVAL2", 5.0),
        _card("CDELT1", 0.05),
        _card("CDELT2", 0.05),
        _card("PC1_1", 1.0),
        _card("PC1_2", 0.1),
        _card("PC2_1", -0.05),
        _card("PC2_2", 1.0),
    ]


def continue_crval_cards() -> list[str]:
    """CRVAL1 split across CONTINUE — tests lexer merge."""
    cards = tan_basic_cards()
    # FITS CONTINUE: opening card omits closing quote; continuation supplies tail + quote.
    cards[9] = "CRVAL1  = '45.12".ljust(CARD_LEN)
    cards.insert(10, "CONTINUE  5'".ljust(CARD_LEN))
    return cards


def header_only_cards() -> list[str]:
    c = tan_basic_cards()
    c[2] = _card("NAXIS", 0)
    return c[:3] + c[5:]


def hierarch_obs_cards() -> list[str]:
    """HIERARCH metadata card preserved in keyword snapshot."""
    cards = tan_basic_cards()
    cards.insert(1, "HIERARCH ESO DPR CATG = 'CALIB'".ljust(CARD_LEN))
    return cards


def main() -> None:
    bundled = Path("/app/fixtures/fits")
    hidden = Path("/opt/verifier-fixtures/fits")
    bundled.mkdir(parents=True, exist_ok=True)
    hidden.mkdir(parents=True, exist_ok=True)

    write_fits(bundled / "tan_basic.fits", tan_basic_cards(), b"\x00" * (200 * 100))
    write_fits(bundled / "sin_basic.fits", sin_basic_cards(), b"\x00" * (200 * 100))
    write_fits(bundled / "pc_skew.fits", pc_skew_cards(), b"\x00" * (64 * 64))
    write_fits(bundled / "header_only.fits", header_only_cards())
    write_fits(hidden / "continue_crval.fits", continue_crval_cards(), b"\x00" * (200 * 100))
    write_fits(hidden / "hierarch_obs.fits", hierarch_obs_cards(), b"\x00" * (200 * 100))
    cards = pc_skew_cards()
    cards[5] = _card("CTYPE1", "RA---SIN")
    cards[6] = _card("CTYPE2", "DEC--SIN")
    write_fits(hidden / "pc_sin_hidden.fits", cards, b"\x00" * (64 * 64))
    print("fits fixtures ready", bundled, hidden)


if __name__ == "__main__":
    main()
