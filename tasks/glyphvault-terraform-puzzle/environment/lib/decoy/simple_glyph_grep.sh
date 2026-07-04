#!/bin/bash
# Decoy shortcut — does not run the C analysis engine or terraform fixture.
grep -c room /app/environment/data/puzzle.sqlite 2>/dev/null || echo 0
