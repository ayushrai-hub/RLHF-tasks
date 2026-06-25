#!/bin/bash
set -euo pipefail
export PATH="/usr/local/go/bin:$PATH"
unset RATELIMIT_WINDOW_MS 2>/dev/null || true

python3 << 'PYEOF'
# Remove profile override AND env var override from config.go
path = '/app/internal/config/config.go'
with open(path) as f: src = f.read()
# Remove from "// Apply profile" to just before "\n\treturn s"
start = src.find('\t// Apply profile overrides')
assert start >= 0, "profile override start not found"
end = src.find('\n\treturn s', start)
assert end >= 0, "return s not found"
src = src[:start] + src[end:]
# Remove strconv import (no longer needed)
src = src.replace('\t"strconv"\n', '')
with open(path, 'w') as f: f.write(src)
print("Removed config overrides + env var")

# Fix loader: ascending sort
path = '/app/internal/loader/loader.go'
with open(path) as f: src = f.read()
old = '\tsort.Sort(sort.Reverse(sort.StringSlice(files)))'
assert old in src, "loader reverse sort not found"
src = src.replace(old, '\tsort.Strings(files)')
with open(path, 'w') as f: f.write(src)
print("Fixed loader sort")

# Fix ratelimit: window boundary inclusive + deny_rate 4dp + penalty boundary + burst count
path = '/app/internal/ratelimit/ratelimit.go'
with open(path) as f: src = f.read()
old = 'if ts > windowStart {'
assert old in src, "window boundary not found"
src = src.replace(old, 'if ts >= windowStart {', 1)

# Fix penalty boundary: <= should be < (strict less-than)
old2 = 'if penaltyEnd, ok := clientPenalty[req.ClientID]; ok && req.TimestampMs <= penaltyEnd {'
assert old2 in src, "penalty boundary not found"
src = src.replace(old2, 'if penaltyEnd, ok := clientPenalty[req.ClientID]; ok && req.TimestampMs < penaltyEnd {')

# Fix burst count: should NOT include current request (+1 is wrong)
old3 = 'if isAllowed && burstCount+1 >= cfg.BurstLimit {'
assert old3 in src, "burst count+1 not found"
src = src.replace(old3, 'if isAllowed && burstCount >= cfg.BurstLimit {')

# Fix client deny_rate: 2dp -> 4dp
old4 = 'math.Round(float64(d.denied)/float64(d.total)*100) / 100'
assert old4 in src, "deny_rate 2dp not found"
src = src.replace(old4, 'roundTo4(float64(d.denied) / float64(d.total))')
with open(path, 'w') as f: f.write(src)
print("Fixed window boundary + penalty boundary + burst count + deny_rate precision")
PYEOF

cd /app && go build -o bin/rate-limiter ./cmd/limiter
mkdir -p /app/output
/app/bin/rate-limiter analyze --traffic /app/data/traffic --output /app/output --format both
