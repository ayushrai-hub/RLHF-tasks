the cronq tool in /app is spitting out wrong fire times for some cron
expressions. it's a little java cli, takes a 5 field cron expr + a start
time and prints the next N times it fires. the json shape is fine, it's
the actual times that are off on certain exprs.

build + run is just

    cd /app && ./build.sh
    java -jar cronq.jar next --expr "0 9 * * MON-FRI" --from "2026-03-01T00:00:00Z" --count 5

the rules it's supposed to follow (expression syntax, the whole
day-of-month vs day-of-week thing, how "next" handles a start time that's
already on a fire minute, the output) are in docs/PROTOCOL.md. that's the
source of truth, the build has to match it for any valid expr not just the
ones i happened to write down. there's an ARCHITECTURE.md if you want the
module map and a TROUBLESHOOTING.md too.

under /app/data there's some example exprs in data/cases/ and a
manifest.json with the right answers for a few of them (worked out from the
protocol, not from the build). handy for sanity checking, but the protocol is
what the build actually has to satisfy.

verifier rebuilds from source so just edit whatever's under /app/src, no
need to check in a jar. and leave /app/data and /app/docs as is, that's the
contract not the thing you're fixing.
