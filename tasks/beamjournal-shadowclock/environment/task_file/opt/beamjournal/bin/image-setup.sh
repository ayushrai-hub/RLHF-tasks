#!/usr/bin/env bash
set -euo pipefail

export PATH="/usr/local/go/bin:/go/bin:${PATH}"
mkdir -p /etc/beamjournal /var/lib/beamjournal /var/log/beamjournal /run/beamjournal /output/beamjournal

cd /opt/beamjournal/src
go build -trimpath -o /usr/local/bin/beamjournal-termrender ./cmd/termrender
go build -trimpath -o /usr/local/bin/beamjournal-fold ./cmd/beamjournal-fold
go build -trimpath -o /usr/local/bin/beamjournald ./cmd/beamjournald

/usr/local/lib/beamjournal/seed.escript /var/lib/beamjournal/journal.bin /var/lib/beamjournal/fold.plan
/usr/local/bin/beamjournal-termrender /opt/beamjournal/etc/config.term /etc/beamjournal/service.toml

chmod +x /usr/local/bin/beamjournal-termrender /usr/local/bin/beamjournal-fold /usr/local/bin/beamjournald /usr/local/sbin/beamjournal-supervise
