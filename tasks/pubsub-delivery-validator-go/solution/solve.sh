#!/bin/bash
set -e
export PATH="/usr/local/go/bin:$PATH"

# Fix 1: Remove config override that disables unsub, duplicate, and retention checks
rm -f /app/config/delivery_mode.toml

# Fix 2: Subscription window uses exclusive end (>= instead of >)
python3 << 'PYEOF'
p = '/app/pkg/validator/validator.go'
with open(p) as f: src = f.read()
old = 'if d.Timestamp < sub.subTS || d.Timestamp > sub.unsubTS {'
assert old in src, f'Patch target not found: Fix 2'
new = 'if d.Timestamp < sub.subTS || d.Timestamp >= sub.unsubTS {'
src = src.replace(old, new, 1)
with open(p, 'w') as f: f.write(src)
PYEOF

# Fix 3: Duplicate detection uses per-client key (msg_id+client_id)
python3 << 'PYEOF'
p = '/app/pkg/validator/validator.go'
with open(p) as f: src = f.read()
old = '''	if cfg.CheckDuplicates {
		seen := make(map[string]string) // msg_id -> first delivery_id
		for _, d := range log.Deliveries {
			if first, exists := seen[d.MsgID]; exists {'''
assert old in src, f'Patch target not found: Fix 3'
new = '''	if cfg.CheckDuplicates {
		seen := make(map[string]string) // msg_id+client -> first delivery_id
		for _, d := range log.Deliveries {
			key := d.MsgID + "|" + d.ClientID
			if first, exists := seen[key]; exists {'''
src = src.replace(old, new, 1)
old2 = '''			} else {
				seen[d.MsgID] = d.DeliveryID'''
assert old2 in src, f'Patch target not found: Fix 3b'
new2 = '''			} else {
				seen[key] = d.DeliveryID'''
src = src.replace(old2, new2, 1)
with open(p, 'w') as f: f.write(src)
PYEOF

# Fix 4: Ordering uses strict increasing (> instead of >=)
python3 << 'PYEOF'
p = '/app/pkg/validator/validator.go'
with open(p) as f: src = f.read()
old = '''			if deliveries[i].SeqNum >= deliveries[i-1].SeqNum {
					continue
				}'''
assert old in src, f'Patch target not found: Fix 4'
new = '''			if deliveries[i].SeqNum > deliveries[i-1].SeqNum {
					continue
				}'''
src = src.replace(old, new, 1)
with open(p, 'w') as f: f.write(src)
PYEOF

# Fix 5: Latency uses floating-point division
python3 << 'PYEOF'
p = '/app/pkg/latency/latency.go'
with open(p) as f: src = f.read()
old = '		meanInterval := float64(totalInterval / int64(len(timestamps)-1))'
assert old in src, f'Patch target not found: Fix 5'
new = '		meanInterval := float64(totalInterval) / float64(len(timestamps)-1)'
src = src.replace(old, new, 1)
with open(p, 'w') as f: f.write(src)
PYEOF

# Fix 6: Dead letter uses >= for retry threshold (not strict >)
python3 << 'PYEOF'
p = '/app/pkg/deadletter/deadletter.go'
with open(p) as f: src = f.read()
old = '		if d.RetryCount > dlCfg.MaxRetryCount {'
assert old in src, f'Patch target not found: Fix 6'
new = '		if d.RetryCount >= dlCfg.MaxRetryCount {'
src = src.replace(old, new, 1)
with open(p, 'w') as f: f.write(src)
PYEOF

# Fix 7: Retention TTL uses strict > (not >=) AND age stats only from expired
python3 << 'PYEOF'
p = '/app/pkg/retention/retention.go'
with open(p) as f: src = f.read()

# Fix 7a: Change >= to > for expiry check
old = '		if age >= ttlMs {'
assert old in src, f'Patch target not found: Fix 7a'
new = '		if age > ttlMs {'
src = src.replace(old, new, 1)

# Fix 7b: Move age tracking inside expiry block
old = '''	var ages []int64
	for _, d := range deliveries {
		firstSeen := msgFirstSeen[d.MsgID]
		age := d.Timestamp - firstSeen
		if age > 0 {
			ages = append(ages, age)
		}
		if age > stats.MaxAge {
			stats.MaxAge = age
		}'''
assert old in src, f'Patch target not found: Fix 7b'
new = '''	var ages []int64
	for _, d := range deliveries {
		firstSeen := msgFirstSeen[d.MsgID]
		age := d.Timestamp - firstSeen'''
src = src.replace(old, new, 1)

# Fix 7c: Track ages and max_age only for expired entries
old = '''		if age > ttlMs {
			stats.TotalExpired++'''
assert old in src, f'Patch target not found: Fix 7c'
new = '''		if age > ttlMs {
			ages = append(ages, age)
			if age > stats.MaxAge {
				stats.MaxAge = age
			}
			stats.TotalExpired++'''
src = src.replace(old, new, 1)

with open(p, 'w') as f: f.write(src)
PYEOF

# Fix 8: Priority normalization divides by total deliveries (not violation count)
python3 << 'PYEOF'
p = '/app/pkg/priority/priority.go'
with open(p) as f: src = f.read()
old = '''	if len(violations) > 0 {
		stats.WeightedViolationScore = math.Round(rawScore/float64(len(violations))*10000) / 10000
	}'''
assert old in src, f'Patch target not found: Fix 8'
new = '''	if len(deliveries) > 0 {
		stats.WeightedViolationScore = math.Round(rawScore/float64(len(deliveries))*10000) / 10000
	}'''
src = src.replace(old, new, 1)
with open(p, 'w') as f: f.write(src)
PYEOF

# Fix 9: Backpressure threshold uses float division for mean interval
python3 << 'PYEOF'
p = '/app/pkg/backpressure/backpressure.go'
with open(p) as f: src = f.read()
old = '''		meanInterval := totalGap / int64(len(timestamps)-1)
		threshold := meanInterval / 2'''
assert old in src, f'Patch target not found: Fix 9'
new = '''		meanIntervalF := float64(totalGap) / float64(len(timestamps)-1)
		threshold := int64(meanIntervalF / 2)'''
src = src.replace(old, new, 1)
with open(p, 'w') as f: f.write(src)
PYEOF

# Fix 10: Throttle bucket uses floor division (not ceiling)
python3 << 'PYEOF'
p = '/app/pkg/throttle/throttle.go'
with open(p) as f: src = f.read()
old = '		bucketSize := int64(math.Ceil(float64(span) / float64(len(dels))))'
assert old in src, f'Patch target not found: Fix 10'
new = '		bucketSize := span / int64(len(dels))'
src = src.replace(old, new, 1)
with open(p, 'w') as f: f.write(src)
PYEOF

# Build and run
cd /app && go build -o /app/bin/pubsub-validator ./cmd/pubsub-validator
mkdir -p /app/output
/app/bin/pubsub-validator --data /app/data/delivery_log.json --config /app/config/pubsub.toml --output /app/output
