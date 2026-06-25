#!/usr/bin/env python3
"""Generate the CryoGrid thermal validation memo (~60k tokens) for the task environment."""

from __future__ import annotations

import hashlib
import textwrap

TARGET_CHARS = 280_000

CANONICAL_RULES = """
SECTION 37 — STAGE CLASS VARIANCE PROPAGATION (NORMATIVE)

CryoGrid OCI simulation bundles list stages under pipeline.stages as a JSON array.
Variance propagation must follow dependency order (topological sort of inputs edges),
not alphabetical stage id order.

For each stage class the propagated variance at stage output is:

SOURCE: var_out = sigma squared where sigma is the stage sigma field.

TRANSFER: var_out = var_in multiplied by (1 + kappa) squared plus epsilon squared.
When epsilon is omitted use 0.01. var_in is the variance from the single input stage.

SINK: var_out equals var_in (pass-through). When multiple inputs connect, var_in is
the sum of input variances.

COUPLER: var_out = (sum of input variances) multiplied by coupling_gain plus sigma squared.
Default coupling_gain is 0.5 when omitted. sigma defaults to 0.0 when omitted.

FEEDBACK: use the TRANSFER formula for variance. FEEDBACK stages participate in loop
gain analysis described in Section 91.

SECTION 58 — FROZEN SOIL CRYO EXCEPTION

When a stage declares cryo_exception with value frozen_soil and the bundle soil_temp
field is strictly below -0.5 degrees C, the stage epsilon floor becomes 0.02 for that
stage only (replace epsilon before applying TRANSFER or FEEDBACK formula).

SECTION 72 — PIPELINE ORDER AND DOT ANNOTATIONS

Graphviz DOT output must list nodes in pipeline.stages array order (not sorted ids).
Each node label must include stage id, var= formatted to six decimal places, and
class= with the stage class string. Edges follow inputs references.

SECTION 91 — UNSTABLE FEEDBACK LOOP DETECTION

Build a directed graph from stage inputs. Detect all directed cycles. For each cycle
compute loop_gain as the product over cycle stages of (1 + kappa) for TRANSFER and
FEEDBACK classes, and 1.0 for other classes. When loop_gain is greater than or equal
to 1.0 the loop is unstable and must appear in metrics unstable_loops with nodes and
gain rounded to six decimals. Set stable to false when any unstable loop exists.
"""


def filler_paragraph(section: int, para: int) -> str:
    seed = f"cryogrid-memo-{section}-{para}".encode()
    digest = hashlib.sha256(seed).hexdigest()
    body = textwrap.fill(
        f"Review panel note {section}.{para}: CryoGrid thermal diffusion validation "
        f"run batch correlation token {digest[:16]}. Field teams recorded borehole "
        f"telemetry drift, snowpack density variance, and latent heat coupling at "
        f"boundary nodes. This paragraph is narrative context only; normative rules "
        f"appear in marked SECTION blocks.",
        width=78,
    )
    return body + "\n\n"


def main() -> None:
    parts: list[str] = [
        "# CryoGrid Thermal Diffusion Validation Memo (OCI Bundle Review)\n\n",
        "Document ID: CG-THERMAL-VALIDATION-2024-REV7\n\n",
        "This memo records multi-year CryoGrid container simulation reviews. "
        "Normative propagation rules are embedded in numbered SECTION blocks.\n\n",
    ]
    section = 1
    while sum(len(p) for p in parts) < TARGET_CHARS - len(CANONICAL_RULES) - 5000:
        parts.append(f"## Chapter {section}\n\n")
        for para in range(1, 25):
            parts.append(filler_paragraph(section, para))
        section += 1
        if section == 37:
            parts.append(CANONICAL_RULES)
            parts.append("\n")
        if section > 200:
            break
    if "SECTION 37" not in "".join(parts):
        parts.append(CANONICAL_RULES)
    text = "".join(parts)
    if len(text) < TARGET_CHARS:
        pad = section
        while len(text) < TARGET_CHARS:
            parts.append(filler_paragraph(pad, 0))
            text = "".join(parts)
            pad += 1
    print(text[:TARGET_CHARS + 5000], end="")


if __name__ == "__main__":
    main()
