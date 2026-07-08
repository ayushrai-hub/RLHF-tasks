"""GeoSynth verifier contract — independent reference math and pytest discovery."""

from __future__ import annotations

import subprocess

from conftest import (
    PIPELINE,
    reference_chain_fingerprint,
    reference_compose_plan,
    reference_confidence_margins,
    reference_depth_epochs,
    reference_epoch_fingerprint,
    reference_feed_fingerprint,
    reference_load_traces,
    reference_margin_table_digest,
    reference_seq_book,
    reference_voxel_edges,
    reference_voxel_fingerprint,
)

from test_hypothesis_ranking import *  # noqa: F403
from test_survey_ingest import *  # noqa: F403

__all__ = [
    "PIPELINE",
    "reference_chain_fingerprint",
    "reference_compose_plan",
    "reference_confidence_margins",
    "reference_depth_epochs",
    "reference_epoch_fingerprint",
    "reference_feed_fingerprint",
    "reference_load_traces",
    "reference_margin_table_digest",
    "reference_seq_book",
    "reference_voxel_edges",
    "reference_voxel_fingerprint",
    "subprocess",
]
