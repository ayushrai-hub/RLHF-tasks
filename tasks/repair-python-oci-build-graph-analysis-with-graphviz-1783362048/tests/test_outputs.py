"""Integration tests for the depmap build-graph tool.

These tests drive the compiled `depmap` binary against the shipped fixtures and
assert on the SQLite database, the build-plan JSON, and the Graphviz DOT graph.
The tool must produce a transitive, version-resolved, deterministically ordered
build plan and a matching dependency graph. Version selection is per-release:
each release of a package declares its own dependency constraints, so the highest
release is not always installable and the resolver has to back off to a lower one
to keep every constraint satisfiable at once. Constraints also use a small grammar:
comma-separated terms are ANDed and '|'-separated groups are ORed, so a version is
acceptable when it satisfies every term of at least one group. Virtual package
providers are chosen by highest provided version, but a candidate is invalid if it
conflicts with the current selection or if its own dep constraints are violated by
the already-chosen package versions — in that case the resolver must try the next
candidate rather than failing or accepting an invalid provider. Conflicts may also
be conditional: a conflict constraint can carry a '; when <package> <constraint>'
marker and only applies while that named package is selected at a version meeting
the marker, staying dormant otherwise. Packages are assigned in ascending NAME
order (not dependency order) during search, so a conflict between an
alphabetically-early package and an alphabetically-late one can force the search to
backtrack across every package in between - the resolver must correctly unwind and
retry, not just check conflicts against immediate neighbors. A regular dependency
(not just a conflict) can carry the same '; when <package> <constraint>' marker: it
only contributes its target to the closure, and only draws an edge, while the named
package ends up selected at a version meeting the marker; while dormant it is as if
the dependency were never declared at all, so its target must not appear anywhere
in the output unless something else in the real build needs it.
"""

import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile

import pytest

DEPMAP = "/usr/local/bin/depmap"
SPECS = "/app/data/specs"
LOCKS = "/app/data/locks/packages.lock.json"
TOOLCHAINS = "/app/data/toolchains.json"

EXPECTED_SPECS = {"web-frontend", "api-service", "batch-worker",
                  "data-pipeline", "ml-trainer", "media-service",
                  "search-service", "telemetry", "rpc-gateway",
                  "log-collector", "cache-tier", "stream-engine",
                  "edge-infra", "auth-relay"}

# The resolved versions. Several packages cannot take their highest release:
#   curl backs off from 8.5.0 to 7.80.0 (8.5.0 needs libssl>=3.0.0 but
#     node-toolchain pins libssl==1.1.1), and libxml2 backs off from 2.11.5 to
#     2.9.14 (2.11.5 needs libpng>=1.6.40 but api-service pins libpng==1.6.37).
#   The arrow->boost->icu chain backtracks three levels at once: data-pipeline
#     bounds icu<=72.1 and ml-trainer excludes icu!=72.1, so the only feasible
#     icu is 70.1; that forces boost down to 1.80.0 (1.83.0 needs icu>=72.1) and
#     in turn arrow down to 12.0.0 (14.0.0 needs boost>=1.83.0). ml-trainer also
#     caps boost<1.85.0 directly. A naive "take the highest version" resolver,
#     or one that only backs off the directly-conflicting package, gets these
#     wrong; the two specs' constraints on the shared icu must combine.
#   The codec chain is driven by a NEGATIVE (conflict) constraint: libwebp 1.3.2
#     declares a conflict against libpng<1.6.40, and api-service pins
#     libpng==1.6.37, so libwebp 1.3.2 is forbidden and libwebp backs off to
#     1.2.4; that in turn forces imaging down to 4.0.0 (5.0.0 needs
#     libwebp>=1.3.0). libjpeg-turbo stays at its highest 3.0.1 because its own
#     conflict (zlib<1.2.11) is NOT triggered by the chosen zlib 1.2.13. A
#     resolver that ignores conflicts picks libwebp 1.3.2 and imaging 5.0.0.
# The search/telemetry chains add DISJUNCTIVE constraints. A constraint may be
# several OR-groups joined by '|', each group a comma-ANDed set of terms; a
# version satisfies it when it meets every term of at least one group.
#   indexer's high release 2.0.0 needs tokenizer>=5.0.0 but telemetry caps
#     tokenizer<4.0.0, so indexer backs off to 1.0.0 whose dep is
#     'tokenizer >=1.0.0,<2.0.0 | >=3.0.0,<4.0.0'; under tokenizer<4.0.0 the
#     highest satisfying release is 3.2.0 (the SECOND group binds).
#   collector's high release 2.0.0 needs analyzer>=4.0.0 but telemetry caps
#     analyzer<3.0.0, so collector backs off to 1.0.0 whose dep is
#     'analyzer >=1.0.0,<2.0.0 | >=4.0.0'; under analyzer<3.0.0 the >=4.0.0 group
#     is empty, so analyzer resolves to 1.5.0 (the FIRST group binds).
#   re2 carries a pure conjunction '>=2.0.0,<2.5.0' from search-service, so it
#     resolves to 2.3.0 (2.7.0 violates <2.5.0). A resolver that reads only the
#     first group, only the last group, or ignores the comma-AND inside a group
#     gets these wrong.
# The rpc-gateway spec adds a COMPATIBLE RELEASE ('~=') constraint. '~= X.Y'
# means '>=X.Y.0 and <(X+1).0.0'. rpc-gateway requires protobuf ~= 3.20
# (i.e. >=3.20.0, <4.0.0). grpc 2.0.0 needs protobuf ~= 4.0 (>=4.0.0, <5.0.0);
# combined with the spec's <4.0.0 cap, no protobuf release satisfies both, so
# grpc backs off to 1.60.0 (which also needs protobuf ~= 3.20). The highest
# protobuf in [3.20.0, 4.0.0) is 3.21.3. A resolver that treats '~=' as plain
# '>=' picks grpc 2.0.0 with protobuf 4.0.0, failing the spec's upper bound.
# rpc-gateway also requires capnproto >=0.9.0. The lock has capnproto releases
# 0.9.0, 0.10.0, 0.11.0 with no further constraints: the highest is 0.11.0.
# The trap: lexicographic string comparison orders "0.9.0" > "0.11.0" (since
# "9" > "1" as a character), picking the wrong answer; the instruction requires
# component-by-component integer comparison, so 0.11.0 > 0.10.0 > 0.9.0.
# The batch-worker spec adds PROVIDER-DEP-FEASIBILITY checking. batch-worker
# requires 'hash-lib >=3.0'. Candidates in descending provided-version order:
#   xxhash@4.0.0 provides hash-lib@4.0 (satisfies >=3.0) but dep 'zlib >=1.3.0'
#     is infeasible: the selected zlib is 1.2.13 which does NOT satisfy >=1.3.0.
#     A resolver that ignores provider dep feasibility picks xxhash@4.0.0 and
#     produces an invalid plan (zlib can't be satisfied at >=1.3.0).
#   xxhash@3.5.0 provides hash-lib@3.5 (satisfies >=3.0) but conflicts with
#     'libssl <2.0.0': selected libssl=1.1.1 satisfies <2.0.0 → conflict fires.
#   murmur3@3.1.0 provides hash-lib@3.1 (satisfies >=3.0), no deps, no
#     triggered conflicts → CHOSEN.
#   murmur3@2.0.0 provides hash-lib@2.0 (does NOT satisfy >=3.0) → not a candidate.
EXPECTED_SELECTED = {
    "curl": "7.80.0",
    "libpng": "1.6.37",
    "libssl": "1.1.1",
    "zlib": "1.2.13",
    "libxml2": "2.9.14",
    "pcre2": "10.42",
    "openjdk-libs": "17.0.9",
    "cacert": "2023.01.10",
    "arrow": "12.0.0",
    "boost": "1.80.0",
    "icu": "70.1",
    "libjpeg-turbo": "3.0.1",
    "libwebp": "1.2.4",
    "imaging": "4.0.0",
    "indexer": "1.0.0",
    "tokenizer": "3.2.0",
    "collector": "1.0.0",
    "analyzer": "1.5.0",
    "re2": "2.3.0",
    "protobuf": "3.21.3",
    "grpc": "1.60.0",
    "capnproto": "0.11.0",
    # Virtual dep provider: log-collector requires compress-lib >=1.3.
    # lz4@2.0.0 provides compress-lib@2.0 (>=1.3) but conflicts with
    # libssl<3.0.0 (selected libssl=1.1.1 triggers it). lz4@1.9.4 provides
    # compress-lib@1.0 (<1.3, doesn't satisfy). zstd@1.5.5 provides
    # compress-lib@1.5 (>=1.3), no conflicts → chosen as the provider.
    "zstd": "1.5.5",
    # Virtual dep provider: batch-worker requires hash-lib >=3.0.
    # xxhash@4.0.0 provides hash-lib@4.0 (>=3.0) but its dep zlib>=1.3.0 is
    # infeasible (selected zlib=1.2.13 < 1.3.0) → rejected on infeasible dep.
    # xxhash@3.5.0 provides hash-lib@3.5 (>=3.0) but conflicts with
    # libssl<2.0.0 (selected libssl=1.1.1 < 2.0.0) → rejected on conflict.
    # murmur3@3.1.0 provides hash-lib@3.1 (>=3.0), no deps, no conflicts → chosen.
    # murmur3@2.0.0 provides hash-lib@2.0 which is <3.0 → not even a candidate.
    "murmur3": "3.1.0",
    # Package extras: search-service requests indexer with extras=['fast','cache'].
    # indexer@1.0.0's 'fast' extra requires simd-lib>=2.0.0 → simd-lib@3.0.0 chosen
    # (highest satisfying release, no deps, no conflicts → accepted).
    # indexer@1.0.0's 'cache' extra requires lru-cache>=1.0.0; lru-cache@2.0.0
    # conflicts with tokenizer<4.0.0 and the selected tokenizer=3.2.0 < 4.0.0
    # → conflict fires, lru-cache@2.0.0 rejected → backs off to lru-cache@1.5.0
    # (no deps, no conflicts → accepted).  Extra deps are resolved with the same
    # backtracking, version-selection, and conflict-checking rules as regular deps.
    "simd-lib": "3.0.0",
    "lru-cache": "1.5.0",
    # Transitive extras: the chosen simd-lib@3.0.0 (pulled in by indexer[fast])
    # itself declares 'vecmath >=4.0', so vecmath joins the closure and is resolved
    # by the same rules. Candidates in descending order:
    #   vecmath@5.0.0 — dep 'cpuflags >=2.0' is infeasible (cpuflags only ships
    #     1.2.0, which is <2.0) → rejected on infeasible dep.
    #   vecmath@4.5.0 — conflicts with 'libssl <2.0.0'; selected libssl=1.1.1
    #     satisfies <2.0.0 → conflict fires → rejected.
    #   vecmath@4.2.0 — no deps, no triggered conflicts → CHOSEN.
    # A resolver that treats extras as flat leaves never expands simd-lib's own dep
    # and misses vecmath entirely (missing node + edge). cpuflags is imported but
    # never selected (its only referrer vecmath@5.0.0 is rejected).
    "vecmath": "4.2.0",
    # CONDITIONAL CONFLICTS: the cache-tier spec pulls in ringbuf, slab, mmapfs and
    # arena. Two conflicts carry a "; when <pkg> <constraint>" marker and only apply
    # while that named package is selected at a version meeting the marker.
    #   ringbuf@2.0.0 declares 'conflict slab >=3.0.0 ; when curl ==7.80.0'. The
    #     selected curl IS 7.80.0, so the marker is ACTIVE and the conflict fires:
    #     slab cannot be >=3.0.0, so it backs off from 3.5.0/3.0.0 to slab@2.0.0.
    #     ringbuf itself stays at its highest 2.0.0 (the conflict targets slab).
    #   mmapfs@2.0.0 declares 'conflict arena >=2.0.0 ; when curl ==8.5.0'. The
    #     selected curl is 7.80.0 (NOT 8.5.0), so the marker is DORMANT and the
    #     conflict does NOT fire: mmapfs keeps its highest release 2.0.0 and arena
    #     keeps its highest 2.5.0. A resolver that ignores the marker and applies
    #     the conflict unconditionally wrongly forces mmapfs down to 1.0.0.
    "ringbuf": "2.0.0",
    "slab": "2.0.0",
    "mmapfs": "2.0.0",
    "arena": "2.5.0",
    # VERSION EPOCHS: the stream-engine spec pulls in codecpad and framebuf.
    # codecpad ships three releases: 2.4.0 (epoch 0), 1!1.0.0 and 1!1.2.0
    # (epoch 1). The epoch dominates version comparison, so 1!1.2.0 outranks
    # 2.4.0 even though 2 > 1 on the plain numbers, and the highest release is
    # 1!1.2.0. A resolver that compares versions as plain dotted integers (or
    # that chokes parsing the '!') mis-ranks these and picks 2.4.0 instead.
    "codecpad": "1!1.2.0",
    # The epoch choice CASCADES: codecpad@1!1.2.0 requires 'framebuf >=3.0.0'
    # (framebuf resolves to 3.2.0), whereas the epoch-0 codecpad@2.4.0 requires
    # 'framebuf >=2.0.0,<3.0.0' (which would pin framebuf at 2.5.0). So an
    # epoch-blind resolver gets BOTH codecpad and framebuf wrong.
    "framebuf": "3.2.0",
    # DEEP CROSS-CLOSURE BACKTRACK: the edge-infra spec pulls in abi-shim and zvfs.
    # abi-shim ships 1.0.0 and 2.0.0 with no deps of its own, so nothing about
    # abi-shim in isolation rules out the higher release. zvfs ships a SINGLE
    # release, 1.0.0, which declares a conflict against 'abi-shim >=2.0.0'. Because
    # the solver assigns packages in ascending NAME order (not dependency order),
    # abi-shim ('a...') is assigned long before zvfs ('z...') - essentially every
    # other package in the whole closure sits between them in the search. A solver
    # greedily picks abi-shim@2.0.0 first (highest preferred) and only discovers
    # the conflict once it reaches zvfs at the far end of the assignment order;
    # zvfs has no other release to try, so the failure must propagate all the way
    # back through every intervening package's search frame to force abi-shim down
    # to 1.0.0, after which the whole tail re-resolves the same way and zvfs's
    # single release becomes valid. A resolver that only checks conflicts locally
    # (adjacent packages) or that does not correctly unwind a deep search stack on
    # failure will leave abi-shim at 2.0.0 and either wrongly accept zvfs or error.
    "abi-shim": "1.0.0",
    "zvfs": "1.0.0",
    # RELEASE-SPECIFIC CLOSURE MEMBERSHIP: log-collector also requires authgate.
    # authgate@1.0.0 (its only release) depends on authtoken>=1.0.0 and also
    # conflicts with authtoken>=2.0.0. authtoken ships two releases: 2.0.0 (whose
    # own dep is 'auditlog >=1.0.0') and 1.5.0 (no deps at all). The solver tries
    # the highest release, authtoken@2.0.0, first; authgate's conflict fires
    # against it, so it backs off to authtoken@1.5.0, which has no deps. Since a
    # package's dependency names differ from release to release, whether a name
    # like auditlog belongs in the final closure depends on which release actually
    # got selected, not on the union of every release's deps: authtoken@1.5.0 (the
    # one actually chosen) never mentions auditlog, so auditlog must NOT appear
    # anywhere in the output even though it's a real dependency of the OTHER,
    # rejected release. A resolver that computes closure membership from the union
    # of all releases' dep names (instead of the selected release's own deps)
    # wrongly includes auditlog as a phantom, unreferenced node.
    "authtoken": "1.5.0",
    "authgate": "1.0.0",
    # EXISTENCE-CONDITIONAL DEPENDENCY: log-collector also requires svc-core.
    # svc-core@1.0.0 (its only release) declares two conditional deps, both gated
    # on the SAME marker package (curl) at two different constraints:
    #   'addon-x >=1.0.0 ; when curl ==7.80.0' - the selected curl IS 7.80.0, so
    #     this marker is ACTIVE: addon-x must join the closure and receive an edge
    #     from svc-core.
    #   'addon-y >=1.0.0 ; when curl ==8.5.0' - the selected curl is 7.80.0, NOT
    #     8.5.0, so this marker is DORMANT: addon-y must NOT appear anywhere, even
    #     though it is a real package in the lock with a satisfying release.
    # A resolver that treats a dependency's marker as decoration (always drawing
    # the edge regardless of the marker) wrongly includes addon-y as a phantom
    # node; one that fails to parse the '; when' suffix at all mis-reads the
    # version constraint on both deps.
    "svc-core": "1.0.0",
    "addon-x": "1.0.0",
    # MARKER-BACKTRACK FEEDBACK: media-service also requires gate-svc and beacon.
    # gate-svc ships 1.0.0 and 2.0.0 with no deps or conflicts of its own, so
    # nothing about gate-svc in isolation rules out the higher release. beacon's
    # only release declares two conditional deps on the SAME marker (gate-svc):
    #   'helper-a >=1.0.0 ; when gate-svc ==2.0.0' and
    #   'helper-b >=1.0.0 ; when gate-svc ==1.0.0'.
    # helper-a in turn declares an UNCONDITIONAL conflict against
    # 'gate-svc >=2.0.0'. A resolver that picks gate-svc's highest release
    # (2.0.0) first activates beacon's conditional dep on helper-a, which then
    # pulls helper-a into the closure - but helper-a's own conflict forbids the
    # very gate-svc release (2.0.0) that activated it. Accepting gate-svc@2.0.0
    # is therefore self-contradicting: the marker's own activation creates the
    # conflict that must reject it. gate-svc must back off to 1.0.0, at which
    # point the OTHER conditional dep flips active instead: 'helper-b >=1.0.0 ;
    # when gate-svc ==1.0.0' now applies, and helper-a's dep is dormant so
    # helper-a must not appear anywhere. A resolver that resolves the marker
    # package first and only then checks whether its conditional dependents are
    # satisfiable (rather than feeding the dependent's own conflicts back into
    # the marker's own version choice) wrongly leaves gate-svc at 2.0.0 and
    # either drops helper-a's conflict or accepts an invalid closure.
    "gate-svc": "1.0.0",
    "beacon": "1.0.0",
    "helper-b": "1.0.0",
    # TRANSITIVE MARKER-CONFLICT CHAIN: auth-relay requires netpivot and
    # relaymgr. netpivot ships 1.0.0/2.0.0 with no deps or conflicts of its
    # own. relaymgr's only release declares two conditional deps on netpivot:
    #   'probe-x >=1.0.0 ; when netpivot ==2.0.0'
    #   'probe-y >=1.0.0 ; when netpivot ==1.0.0'
    # Unlike the media-service marker-backtrack case (where the conflict sits
    # directly on the marker's target), the conflict here is ONE HOP DEEPER:
    # probe-x's own release carries an UNCONDITIONAL dep on linkmod, and
    # linkmod's single release carries an UNCONDITIONAL conflict against
    # 'netpivot >=2.0.0'. Both probe-x and linkmod are real closure members
    # (by name) regardless of whether relaymgr's marker-gated edge to probe-x
    # ever fires, so linkmod's conflict against netpivot applies unconditionally
    # during search. Accepting netpivot@2.0.0 is therefore self-contradicting:
    # it would (transitively, through probe-x's own unconditional dependency)
    # require linkmod, but linkmod forbids the very netpivot release that
    # brought it in reach. netpivot must back off to 1.0.0, at which point
    # relaymgr's OTHER conditional dep flips active: 'probe-y >=1.0.0 ; when
    # netpivot ==1.0.0'. A resolver that only checks a marker's DIRECT target
    # for a feedback conflict (and does not propagate conflicts through that
    # target's own further dependencies) wrongly leaves netpivot at 2.0.0.
    "netpivot": "1.0.0",
    "relaymgr": "1.0.0",
    "probe-y": "1.0.0",
}

EXPECTED_TOOLCHAINS = {
    "base-gcc": "12.2.0",
    "node-toolchain": "20.1.0",
    "python-toolchain": "3.11.4",
    "jdk-toolchain": "17.0.9",
}

EXPECTED_NODE_COUNT = 63  # 59 prior + auth-relay spec + netpivot + relaymgr + probe-y (probe-x, linkmod excluded, see below)
EXPECTED_EDGE_COUNT = 72  # 69 prior + auth-relay->netpivot + auth-relay->relaymgr + relaymgr->probe-y

# The resolved build order, determined by Kahn's algorithm with lexicographic
# tie-breaking on node id.  Two spec-ordering constraints change the order
# relative to a plain package-dep sort:
#
# Constraint 1: data-pipeline requires search-service.
#   Without this, data-pipeline would be placed first among TC-free specs
#   (alphabetically: d < l < m < m < r < s < t).  With the constraint,
#   data-pipeline must wait until search-service is placed.
#   The queue of TC-free ready specs (after all pkg:* are placed) excludes
#   data-pipeline; it goes: log-collector → media-service → ml-trainer →
#   rpc-gateway → search-service.  Once search-service lands, both
#   data-pipeline and telemetry become ready; 'd' < 't' so data-pipeline
#   goes next, then telemetry.
#
# Constraint 2: web-frontend requires api-service.
#   Without this, the TC tail is: node-toolchain → web-frontend →
#   python-toolchain → api-service.  With the constraint, web-frontend must
#   wait for api-service, which in turn waits for python-toolchain.  So
#   python-toolchain and api-service must both finish before web-frontend.
#   The new TC tail becomes: python-toolchain → api-service → web-frontend.
#
# Package extras add two new leaf nodes (simd-lib, lru-cache) resolved via
# indexer@1.0.0's extras, requested by search-service with extras=['fast','cache'].
# Both are leaf nodes (no deps) and join the ready queue immediately; they are
# placed in the pkg:* window with the same lexicographic tie-break:
#   lru-cache at pos 7 ('l' < 'm', between arrow and murmur3)
#   simd-lib  at pos 13 ('si' < 't', between re2 and tokenizer)
# indexer@1.0.0 is now delayed to pos 15 (waits for tokenizer, simd-lib, lru-cache).
# cache-tier adds ringbuf, slab, mmapfs, arena (all leaf packages, no deps) and the
# spec:cache-tier node. arena sorts right after analyzer ('are' > 'ana'); mmapfs
# sorts between lru-cache and murmur3 ('mm' < 'mu'); ringbuf sorts after re2
# ('ri' > 're') and before slab; slab sorts after ringbuf and before tokenizer.
# spec:cache-tier is TC-free with no requires_specs, so it joins the ready spec
# window in ascending-id order (it precedes spec:log-collector: 'ca' < 'lo').
# edge-infra adds abi-shim and zvfs, both leaf packages (no deps of their own).
# abi-shim's id sorts before every other package name in the closure ('abi-shim'
# < 'analyzer'), so it lands at position 0. zvfs sorts after every other package
# name ('zvfs' > 'zstd'), landing right before the spec window. spec:edge-infra
# itself is TC-free with no requires_specs and sorts right after spec:cache-tier
# ('ca' < 'ed' < 'lo').
EXPECTED_ORDER = [
    "pkg:abi-shim@1.0.0",
    # addon-x is a leaf (no deps of its own) pulled in only via svc-core's ACTIVE
    # conditional dep ('addon-x >=1.0.0 ; when curl ==7.80.0'); it's ready from
    # step 1 and sorts right after abi-shim ('add' < 'ana').
    "pkg:addon-x@1.0.0",
    "pkg:analyzer@1.5.0",
    "pkg:arena@2.5.0",
    # authtoken is a leaf once the resolver backs off to its 1.5.0 release (no
    # deps); it's ready from step 1 and sorts after arena, before authgate/cacert.
    "pkg:authtoken@1.5.0",
    "pkg:authgate@1.0.0",
    "pkg:cacert@2023.01.10",
    "pkg:capnproto@0.11.0",
    "pkg:collector@1.0.0",
    # stream-engine's epoch cluster: framebuf is a leaf and is ready from step 1;
    # codecpad@1!1.2.0 depends on framebuf so it waits for framebuf to be placed.
    # framebuf sorts after collector ('f' > 'c') and codecpad follows once ready.
    "pkg:framebuf@3.2.0",
    "pkg:codecpad@1!1.2.0",
    # gate-svc and helper-b are both leaves (gate-svc backs off with no deps of
    # its own; helper-b's conditional dep is what draws beacon's edge to it) so
    # both are ready from step 1 and sort ascending ('gate-svc' < 'helper-b').
    # beacon becomes ready only once helper-b is placed and follows immediately.
    "pkg:gate-svc@1.0.0",
    "pkg:helper-b@1.0.0",
    "pkg:beacon@1.0.0",
    "pkg:icu@70.1",
    "pkg:boost@1.80.0",
    "pkg:arrow@12.0.0",
    "pkg:lru-cache@1.5.0",
    # mmapfs is a leaf (its dormant conditional conflict adds no edge), ready from
    # step 1; sorts between lru-cache ('l') and murmur3 ('mu'):
    "pkg:mmapfs@2.0.0",
    "pkg:murmur3@3.1.0",
    # netpivot is a leaf once backed off to 1.0.0 (no deps of its own); it's
    # ready from step 1 and sorts after murmur3, before pcre2.
    "pkg:netpivot@1.0.0",
    "pkg:pcre2@10.42",
    # probe-y is a leaf (no deps) drawn in only via relaymgr's now-ACTIVE
    # conditional dep ('probe-y >=1.0.0 ; when netpivot ==1.0.0'); it's ready
    # from step 1 and sorts after pcre2, before protobuf.
    "pkg:probe-y@1.0.0",
    "pkg:protobuf@3.21.3",
    "pkg:grpc@1.60.0",
    "pkg:re2@2.3.0",
    # relaymgr becomes ready only once probe-y is placed; it sorts after re2,
    # before ringbuf ('re2' < 'relaymgr' < 'ringbuf').
    "pkg:relaymgr@1.0.0",
    # ringbuf and slab are leaves (the active conditional conflict only backs slab
    # off a version; it adds no edge). ringbuf sorts after relaymgr, slab after ringbuf:
    "pkg:ringbuf@2.0.0",
    "pkg:slab@2.0.0",
    # svc-core's only real edge is to addon-x (placed at step 1); its dep on
    # addon-y is dormant and draws no edge, so svc-core is ready almost
    # immediately and simply sorts by id: after slab, before tokenizer
    # ('sl' < 'sv' < 'to').
    "pkg:svc-core@1.0.0",
    "pkg:tokenizer@3.2.0",
    "pkg:vecmath@4.2.0",
    "pkg:simd-lib@3.0.0",
    "pkg:indexer@1.0.0",
    "pkg:zlib@1.2.13",
    "pkg:libjpeg-turbo@3.0.1",
    "pkg:libpng@1.6.37",
    "pkg:libssl@1.1.1",
    "pkg:curl@7.80.0",
    "pkg:libwebp@1.2.4",
    "pkg:imaging@4.0.0",
    "pkg:libxml2@2.9.14",
    "pkg:openjdk-libs@17.0.9",
    "pkg:zstd@1.5.5",
    "pkg:zvfs@1.0.0",
    # spec:auth-relay is ready once netpivot and relaymgr are placed; among the
    # initially-ready TC-free specs it sorts first ('au' < 'ca' < 'ed' < 'lo'):
    "spec:auth-relay",
    # spec:cache-tier is ready once its four leaf packages are placed; among the
    # initially-ready TC-free specs it sorts next ('ca' < 'ed' < 'lo'):
    "spec:cache-tier",
    "spec:edge-infra",
    "spec:log-collector",
    "spec:media-service",
    "spec:ml-trainer",
    "spec:rpc-gateway",
    "spec:search-service",
    "spec:data-pipeline",
    # spec:stream-engine is TC-free with no requires_specs; it becomes ready once
    # its two packages are placed and sorts after data-pipeline, before telemetry.
    "spec:stream-engine",
    "spec:telemetry",
    "tc:base-gcc@12.2.0",
    "tc:jdk-toolchain@17.0.9",
    "spec:batch-worker",
    "tc:node-toolchain@20.1.0",
    "tc:python-toolchain@3.11.4",
    "spec:api-service",
    "spec:web-frontend",
]

EXPECTED_DB_TABLES = {
    "specs",
    "spec_packages",
    "spec_toolchains",
    "spec_ordering",
    "packages",
    "package_deps",
    "package_conflicts",
    "package_provides",
    "package_extras",
    "toolchains",
    "toolchain_req_toolchains",
    "toolchain_req_packages",
}


def run_pipeline(workdir):
    """Run import, plan and graph into workdir; return (db, plan_path, dot_path)."""
    os.makedirs(workdir, exist_ok=True)
    db = os.path.join(workdir, "build.db")
    plan = os.path.join(workdir, "build-plan.json")
    dot = os.path.join(workdir, "depgraph.dot")
    subprocess.run(
        [DEPMAP, "import", "--specs", SPECS, "--locks", LOCKS,
         "--toolchains", TOOLCHAINS, "--db", db],
        check=True, capture_output=True, text=True,
    )
    subprocess.run([DEPMAP, "plan", "--db", db, "--out", plan],
                   check=True, capture_output=True, text=True)
    subprocess.run([DEPMAP, "graph", "--db", db, "--out", dot],
                   check=True, capture_output=True, text=True)
    return db, plan, dot


@pytest.fixture(scope="session")
def outputs():
    """Build the canonical outputs once for the whole test session."""
    assert os.path.exists(DEPMAP), "depmap binary was not built"
    workdir = "/app/out"
    db, plan_path, dot_path = run_pipeline(workdir)
    with open(plan_path) as f:
        plan = json.load(f)
    with open(dot_path) as f:
        dot = f.read()
    return {"db": db, "plan": plan, "dot": dot,
            "plan_path": plan_path, "dot_path": dot_path}


def parse_dot(dot):
    """Return (nodes: dict id->type, edges: set of (src, dst)) from DOT text."""
    nodes = {}
    edges = set()
    node_re = re.compile(r'^\s*"([^"]+)"\s*\[type="([^"]+)"\]\s*;\s*$')
    edge_re = re.compile(r'^\s*"([^"]+)"\s*->\s*"([^"]+)"\s*;\s*$')
    for line in dot.splitlines():
        m = node_re.match(line)
        if m:
            nodes[m.group(1)] = m.group(2)
            continue
        m = edge_re.match(line)
        if m:
            edges.add((m.group(1), m.group(2)))
    return nodes, edges


def test_outputs_exist(outputs):
    """import, plan and graph must produce all three output files."""
    assert os.path.exists(outputs["db"])
    assert os.path.exists(outputs["plan_path"])
    assert os.path.exists(outputs["dot_path"])


def test_build_db_schema(outputs):
    """build.db must be a real SQLite database with the normalized schema."""
    con = sqlite3.connect(outputs["db"])
    try:
        rows = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    finally:
        con.close()
    tables = {r[0] for r in rows}
    assert EXPECTED_DB_TABLES.issubset(tables), f"missing tables: {EXPECTED_DB_TABLES - tables}"


def test_build_db_imported_full_lock(outputs):
    """Every package in the lock (including bzip2, lz4, xxhash, cpuflags, and
    auditlog which are not selected) must be imported into the DB. murmur3 IS
    selected (as the hash-lib provider for batch-worker); xxhash is imported but
    rejected as a provider. simd-lib and lru-cache ARE selected (as extra deps of
    indexer@1.0.0 via the search-service extras=['fast','cache'] request), and
    vecmath IS selected as simd-lib@3.0.0's own transitive dep. cpuflags is
    imported but never selected — its only referrer vecmath@5.0.0 is rejected on
    an infeasible dep. auditlog is imported but never selected — its only
    referrer, authtoken@2.0.0, is rejected (authgate conflicts with it), and the
    chosen authtoken@1.5.0 has no deps at all. addon-y is imported but never
    selected — it has a satisfying release, but its only referrer is svc-core's
    dependency on it, which carries a '; when curl ==8.5.0' marker that stays
    dormant since the selected curl is 7.80.0. helper-a is imported but never
    selected — beacon's conditional dep on it only activates while gate-svc is
    2.0.0, but gate-svc must back off to 1.0.0 (helper-a's own conflict forbids
    the very gate-svc release that would activate it), so the marker stays
    dormant at the resolved gate-svc=1.0.0. probe-x and linkmod are imported
    but never selected — relaymgr's conditional dep on probe-x only activates
    while netpivot is 2.0.0, but netpivot must back off to 1.0.0 because
    probe-x's own unconditional dep pulls in linkmod, whose unconditional
    conflict forbids the very netpivot release that would activate the
    marker, so the marker never fires and probe-x (with its whole sub-closure,
    linkmod included) never gets an edge drawn to it."""
    con = sqlite3.connect(outputs["db"])
    try:
        names = {r[0] for r in con.execute("SELECT DISTINCT name FROM packages").fetchall()}
        specs = {r[0] for r in con.execute("SELECT name FROM specs").fetchall()}
    finally:
        con.close()
    assert "bzip2" in names, "import dropped the unreferenced bzip2 package"
    assert "lz4" in names, "import dropped lz4 (in lock but not selected as provider)"
    assert "xxhash" in names, "import dropped xxhash (in lock but rejected as hash-lib provider)"
    assert "cpuflags" in names, "import dropped cpuflags (in lock but not selected)"
    assert "auditlog" in names, "import dropped auditlog (in lock but not selected)"
    assert "addon-y" in names, "import dropped addon-y (in lock but never selected: its dependent marker is dormant)"
    assert "helper-a" in names, "import dropped helper-a (in lock but never selected: its marker never activates)"
    assert "probe-x" in names, "import dropped probe-x (in lock but never selected: its marker never activates)"
    assert "linkmod" in names, "import dropped linkmod (in lock but never selected: only reachable through probe-x's dormant marker)"
    expected_all = set(EXPECTED_SELECTED) | {
        "bzip2", "lz4", "xxhash", "cpuflags", "auditlog", "addon-y", "helper-a",
        "probe-x", "linkmod",
    }
    assert names == expected_all, \
        f"lock packages differ: {names.symmetric_difference(expected_all)}"
    assert specs == EXPECTED_SPECS


def test_package_deps_are_per_version(outputs):
    """package_deps is keyed by (package, version): different releases of the
    same package can declare different dependency constraints."""
    con = sqlite3.connect(outputs["db"])
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(package_deps)").fetchall()}
        curl = {
            (v, dep): con_
            for (v, dep, con_) in con.execute(
                "SELECT version, dep, ver_constraint FROM package_deps WHERE package='curl'"
            ).fetchall()
        }
    finally:
        con.close()
    assert "version" in cols, "package_deps must record the release version"
    # curl 8.5.0 needs a newer libssl than curl 7.80.0 does.
    assert curl[("8.5.0", "libssl")] == ">=3.0.0"
    assert curl[("7.80.0", "libssl")] == ">=1.1.1"


def test_package_conflicts_imported(outputs):
    """Conflicts are imported per (package, version): a release can forbid a
    range of another package. These negative constraints drive the codec chain."""
    con = sqlite3.connect(outputs["db"])
    try:
        cols = {r[1] for r in con.execute(
            "PRAGMA table_info(package_conflicts)").fetchall()}
        rows = {
            (p, v, cf): c
            for (p, v, cf, c) in con.execute(
                "SELECT package, version, conflict, ver_constraint FROM package_conflicts"
            ).fetchall()
        }
    finally:
        con.close()
    assert {"package", "version", "conflict", "ver_constraint"}.issubset(cols)
    # libwebp 1.3.2 cannot sit on an old libpng ABI.
    assert rows[("libwebp", "1.3.2", "libpng")] == "<1.6.40"
    # libjpeg-turbo 3.0.1 carries a conflict that the chosen zlib does not trip.
    assert rows[("libjpeg-turbo", "3.0.1", "zlib")] == "<1.2.11"


def test_plan_structure(outputs):
    """The plan JSON has build_order, node_count, edge_count with typed nodes."""
    plan = outputs["plan"]
    assert set(plan.keys()) >= {"build_order", "node_count", "edge_count"}
    for n in plan["build_order"]:
        assert set(n.keys()) >= {"id", "type", "name", "version", "depends_on"}
        assert n["type"] in {"spec", "package", "toolchain"}
        assert isinstance(n["depends_on"], list)


def test_node_and_edge_counts(outputs):
    """Node and edge counts match the resolved build closure."""
    plan = outputs["plan"]
    assert plan["node_count"] == EXPECTED_NODE_COUNT
    assert len(plan["build_order"]) == EXPECTED_NODE_COUNT
    assert plan["edge_count"] == EXPECTED_EDGE_COUNT
    total_edges = sum(len(n["depends_on"]) for n in plan["build_order"])
    assert total_edges == EXPECTED_EDGE_COUNT


def test_all_specs_present(outputs):
    """Every spec appears as a node in the plan."""
    plan = outputs["plan"]
    spec_names = {n["name"] for n in plan["build_order"] if n["type"] == "spec"}
    assert spec_names == EXPECTED_SPECS


def test_closure_packages_exact(outputs):
    """Only packages reachable from a spec appear; unreferenced ones are excluded.
    zstd appears as the resolved provider for the virtual dep 'compress-lib >=1.3'.
    murmur3 appears as the resolved provider for the virtual dep 'hash-lib >=3.0'.
    simd-lib and lru-cache appear as extras deps of indexer@1.0.0, resolved via
    search-service's extras=['fast','cache'] request. lru-cache@1.5.0 is chosen
    because lru-cache@2.0.0 conflicts with tokenizer<4.0.0 (tokenizer=3.2.0).
    lz4 is in the lock but is not chosen (1.9.4 provides compress-lib 1.0 <1.3;
    2.0.0 provides 2.0 >=1.3 but conflicts with libssl<3.0.0). bzip2 is also
    unreferenced. xxhash is in the lock but rejected (4.0.0 has infeasible dep
    zlib>=1.3.0; 3.5.0 conflicts with libssl<2.0.0). vecmath IS in the closure as
    simd-lib@3.0.0's transitive dep. cpuflags is in the lock but NOT in the closure:
    its only referrer vecmath@5.0.0 is rejected on the infeasible dep cpuflags>=2.0
    (cpuflags only ships 1.2.0). auditlog is in the lock but NOT in the closure: its
    only referrer authtoken@2.0.0 is rejected (authgate conflicts with it), and the
    chosen authtoken@1.5.0 has no deps at all. addon-y is in the lock but NOT in the
    closure: svc-core's dependency on it carries a '; when curl ==8.5.0' marker that
    stays dormant (the selected curl is 7.80.0), so no edge is ever drawn to it."""
    plan = outputs["plan"]
    pkg_names = {n["name"] for n in plan["build_order"] if n["type"] == "package"}
    assert pkg_names == set(EXPECTED_SELECTED)
    assert "bzip2" not in pkg_names
    assert "lz4" not in pkg_names, \
        "lz4 must not be in closure: its versions either don't satisfy >=1.3 or conflict"
    assert "xxhash" not in pkg_names, (
        "xxhash must not be in closure: 4.0.0 rejected (dep zlib>=1.3.0 infeasible, "
        "zlib=1.2.13<1.3.0); 3.5.0 rejected (conflict libssl<2.0.0, libssl=1.1.1<2.0.0)"
    )
    assert "vecmath" in pkg_names, \
        "vecmath must be in closure (transitive dep of simd-lib@3.0.0 via indexer[fast])"
    assert "cpuflags" not in pkg_names, (
        "cpuflags must not be in closure: its only referrer vecmath@5.0.0 is rejected "
        "(dep cpuflags>=2.0 infeasible, cpuflags only ships 1.2.0)"
    )
    assert "auditlog" not in pkg_names, (
        "auditlog must not be in closure: its only referrer authtoken@2.0.0 is "
        "rejected (authgate conflicts with authtoken>=2.0.0), and the chosen "
        "authtoken@1.5.0 has no deps at all"
    )
    assert "addon-x" in pkg_names, (
        "addon-x must be in closure: svc-core's dependency on it carries "
        "'; when curl ==7.80.0', and the selected curl IS 7.80.0"
    )
    assert "addon-y" not in pkg_names, (
        "addon-y must not be in closure: svc-core's dependency on it carries "
        "'; when curl ==8.5.0', and the selected curl is 7.80.0, not 8.5.0, so "
        "the marker stays dormant and no edge is ever drawn to it"
    )
    assert "gate-svc" in pkg_names and "beacon" in pkg_names, (
        "gate-svc and beacon must be in closure: both are direct media-service "
        "spec packages"
    )
    assert "helper-b" in pkg_names, (
        "helper-b must be in closure: beacon's dependency on it carries "
        "'; when gate-svc ==1.0.0', and gate-svc backs off to 1.0.0"
    )
    assert "helper-a" not in pkg_names, (
        "helper-a must not be in closure: beacon's dependency on it carries "
        "'; when gate-svc ==2.0.0', but gate-svc must back off to 1.0.0 because "
        "helper-a's own conflict forbids the very gate-svc release (2.0.0) that "
        "would activate the marker in the first place, so the marker never fires"
    )
    assert "netpivot" in pkg_names and "relaymgr" in pkg_names, (
        "netpivot and relaymgr must be in closure: both are direct auth-relay "
        "spec packages"
    )
    assert "probe-y" in pkg_names, (
        "probe-y must be in closure: relaymgr's dependency on it carries "
        "'; when netpivot ==1.0.0', and netpivot backs off to 1.0.0"
    )
    assert "probe-x" not in pkg_names, (
        "probe-x must not be in closure: relaymgr's dependency on it carries "
        "'; when netpivot ==2.0.0', but netpivot must back off to 1.0.0 because "
        "probe-x's own unconditional dep on linkmod, whose unconditional conflict "
        "forbids netpivot >=2.0.0, makes 2.0.0 self-contradicting"
    )
    assert "linkmod" not in pkg_names, (
        "linkmod must not be in closure: it is only reachable through probe-x, "
        "whose own marker-gated edge from relaymgr never fires"
    )


def test_toolchains_present(outputs):
    """All transitively required toolchains appear with their versions."""
    plan = outputs["plan"]
    tcs = {n["name"]: n["version"] for n in plan["build_order"] if n["type"] == "toolchain"}
    assert tcs == EXPECTED_TOOLCHAINS


def test_selected_versions_exact(outputs):
    """Each package resolves to the highest version that keeps ALL constraints
    (including those induced by other packages' chosen releases) satisfiable."""
    plan = outputs["plan"]
    selected = {n["name"]: n["version"] for n in plan["build_order"] if n["type"] == "package"}
    assert selected == EXPECTED_SELECTED


def test_version_backtracking(outputs):
    """The resolver must back off from the highest release when it would make the
    constraint set unsatisfiable; a greedy 'highest version' pick fails here."""
    plan = outputs["plan"]
    selected = {n["name"]: n["version"] for n in plan["build_order"] if n["type"] == "package"}
    assert selected["curl"] == "7.80.0", "curl 8.5.0 conflicts with libssl==1.1.1"
    assert selected["libssl"] == "1.1.1", "node-toolchain pins libssl==1.1.1"
    assert selected["libxml2"] == "2.9.14", "libxml2 2.11.5 conflicts with libpng==1.6.37"
    assert selected["libpng"] == "1.6.37", "api-service pins libpng==1.6.37"


def test_cascading_backtracking_across_specs(outputs):
    """The arrow->boost->icu chain must backtrack three levels. data-pipeline
    bounds icu<=72.1 and ml-trainer excludes icu!=72.1, so the shared icu is
    forced to 70.1; that cascades boost down to 1.80.0 and arrow down to 12.0.0.
    A resolver that ignores the <=, <, or != operators, or that does not combine
    the two specs' constraints on the shared icu, picks higher versions and
    fails."""
    plan = outputs["plan"]
    selected = {n["name"]: n["version"] for n in plan["build_order"] if n["type"] == "package"}
    assert selected["icu"] == "70.1", "icu<=72.1 and icu!=72.1 leave only 70.1"
    assert selected["boost"] == "1.80.0", "boost 1.83.0 needs icu>=72.1; also boost<1.85.0"
    assert selected["arrow"] == "12.0.0", "arrow 14.0.0 needs boost>=1.83.0"


def test_conflict_forces_backoff(outputs):
    """A negative (conflict) constraint, not a version dependency, drives the
    codec chain. libwebp 1.3.2 conflicts with libpng<1.6.40 and libpng is pinned
    at 1.6.37, so libwebp must back off to 1.2.4, which forces imaging down to
    4.0.0 (5.0.0 needs libwebp>=1.3.0). A resolver that ignores conflicts keeps
    libwebp at 1.3.2 and imaging at 5.0.0. libjpeg-turbo stays at its highest
    3.0.1 because its conflict (zlib<1.2.11) is not satisfied by zlib 1.2.13 -
    a resolver that treats every conflict as blocking would wrongly drop it."""
    plan = outputs["plan"]
    selected = {n["name"]: n["version"] for n in plan["build_order"] if n["type"] == "package"}
    assert selected["libwebp"] == "1.2.4", "libwebp 1.3.2 conflicts with libpng==1.6.37"
    assert selected["imaging"] == "4.0.0", "imaging 5.0.0 needs libwebp>=1.3.0"
    assert selected["libjpeg-turbo"] == "3.0.1", "its conflict (zlib<1.2.11) is not triggered"


def test_conditional_conflict_resolution(outputs):
    """Conflicts may carry a '; when <package> <constraint>' marker and only apply
    while that named package is selected at a version meeting the marker; otherwise
    the conflict is dormant. The cache-tier spec pulls in ringbuf, slab, mmapfs and
    arena to exercise BOTH branches independently:

      ACTIVE branch: ringbuf@2.0.0 declares 'conflict slab >=3.0.0 ; when curl
        ==7.80.0'. The selected curl IS 7.80.0, so the marker is active and the
        conflict fires: slab cannot take 3.5.0 or 3.0.0 and backs off to 2.0.0.
        ringbuf itself stays at its highest 2.0.0 (the conflict targets slab).

      DORMANT branch: mmapfs@2.0.0 declares 'conflict arena >=2.0.0 ; when curl
        ==8.5.0'. The selected curl is 7.80.0, NOT 8.5.0, so the marker is dormant
        and the conflict does NOT fire: mmapfs keeps its highest release 2.0.0 and
        arena keeps its highest 2.5.0.

    A resolver that ignores the marker and treats the conflict as unconditional
    applies mmapfs's conflict against arena@2.5.0 and wrongly forces mmapfs down to
    1.0.0 (that is the exact divergence this test guards). A resolver that fails to
    parse the '; when' suffix at all mis-reads the version constraint on slab and
    keeps slab at 3.5.0."""
    plan = outputs["plan"]
    selected = {n["name"]: n["version"] for n in plan["build_order"] if n["type"] == "package"}
    by_id = {n["id"]: n for n in plan["build_order"]}

    # Active marker: the conflict fires, backing slab off; ringbuf stays highest.
    assert selected["ringbuf"] == "2.0.0", "ringbuf stays highest; its conflict targets slab"
    assert selected["slab"] == "2.0.0", (
        "ringbuf@2.0.0's conditional conflict 'slab >=3.0.0 ; when curl ==7.80.0' is "
        "ACTIVE (curl=7.80.0), so slab cannot be >=3.0.0 and backs off to 2.0.0"
    )
    # Dormant marker: the conflict does NOT fire; mmapfs and arena stay highest.
    assert selected["mmapfs"] == "2.0.0", (
        "mmapfs@2.0.0's conditional conflict 'arena >=2.0.0 ; when curl ==8.5.0' is "
        "DORMANT (curl=7.80.0 != 8.5.0); a resolver that ignores the marker wrongly "
        "forces mmapfs down to 1.0.0"
    )
    assert selected["arena"] == "2.5.0", "arena keeps its highest release; mmapfs's conflict is dormant"

    # cache-tier depends on all four cluster packages at their resolved versions.
    cache = by_id.get("spec:cache-tier")
    assert cache is not None, "spec:cache-tier must be in the plan"
    for dep in ("pkg:ringbuf@2.0.0", "pkg:slab@2.0.0",
                "pkg:mmapfs@2.0.0", "pkg:arena@2.5.0"):
        assert dep in cache["depends_on"], f"cache-tier must depend on {dep}"

    # The conditional conflicts must be imported verbatim (marker embedded in the
    # conflict constraint string) so the resolver can parse the '; when' clause.
    con = sqlite3.connect(outputs["db"])
    try:
        rows = {
            (p, v, cf): c
            for (p, v, cf, c) in con.execute(
                "SELECT package, version, conflict, ver_constraint FROM package_conflicts "
                "WHERE package IN ('ringbuf', 'mmapfs')"
            ).fetchall()
        }
    finally:
        con.close()
    assert rows[("ringbuf", "2.0.0", "slab")] == ">=3.0.0 ; when curl ==7.80.0"
    assert rows[("mmapfs", "2.0.0", "arena")] == ">=2.0.0 ; when curl ==8.5.0"


def test_conditional_dependency_membership(outputs):
    """The '; when <package> <constraint>' marker also applies to regular
    dependencies, not just conflicts: a dependency only contributes its target to
    the closure, and only draws an edge, while the named marker package ends up
    selected at a version meeting the marker. log-collector pulls in svc-core,
    whose only release declares two conditional deps gated on the SAME marker
    package (curl) at two different constraints, exercising BOTH branches:

      ACTIVE branch: 'addon-x >=1.0.0 ; when curl ==7.80.0'. The selected curl IS
        7.80.0, so the marker is active: addon-x must join the closure, appear as
        a node, and receive an edge from svc-core.

      DORMANT branch: 'addon-y >=1.0.0 ; when curl ==8.5.0'. The selected curl is
        7.80.0, NOT 8.5.0, so the marker is dormant: addon-y must NOT appear
        anywhere in the output, not as a node and not as an edge target, even
        though it is a real package in the lock with a satisfying release.

    A resolver that treats a dependency's marker as inert decoration (always
    including the target regardless of the marker, the way a naive port of the
    conflict-only marker logic might) wrongly includes addon-y as a phantom node
    with no real referrer. A resolver that fails to parse the '; when' suffix at
    all mis-reads the plain version constraint on both deps."""
    plan = outputs["plan"]
    selected = {n["name"]: n["version"] for n in plan["build_order"] if n["type"] == "package"}
    by_id = {n["id"]: n for n in plan["build_order"]}
    node_ids = {n["id"] for n in plan["build_order"]}
    all_deps = {d for n in plan["build_order"] for d in n["depends_on"]}

    assert selected.get("curl") == "7.80.0", "the marker package curl must resolve to 7.80.0"
    assert selected.get("svc-core") == "1.0.0", "svc-core is log-collector's only release"

    # Active branch: addon-x must be a real node with an edge from svc-core.
    assert selected.get("addon-x") == "1.0.0", (
        "addon-x must be selected: svc-core's conditional dep on it "
        "('; when curl ==7.80.0') is ACTIVE since the selected curl IS 7.80.0"
    )
    svc_core = by_id.get("pkg:svc-core@1.0.0")
    assert svc_core is not None, "pkg:svc-core@1.0.0 must be in the plan"
    assert svc_core["depends_on"] == ["pkg:addon-x@1.0.0"], (
        "svc-core must depend on exactly pkg:addon-x@1.0.0: the addon-x edge is "
        "active, and the addon-y edge is dormant and must not be drawn"
    )

    # Dormant branch: addon-y must not appear anywhere, under any version.
    assert "addon-y" not in selected, (
        "addon-y must not be selected: svc-core's conditional dep on it "
        "('; when curl ==8.5.0') stays DORMANT since the selected curl is 7.80.0"
    )
    assert not any(nid.startswith("pkg:addon-y@") for nid in node_ids), \
        "addon-y must not appear as a node under any version"
    assert not any(d.startswith("pkg:addon-y@") for d in all_deps), \
        "no node may depend on addon-y; its only dependency edge is dormant"

    # log-collector must depend on the new svc-core node.
    log_col = by_id.get("spec:log-collector")
    assert log_col is not None, "spec:log-collector must be in the plan"
    assert "pkg:svc-core@1.0.0" in log_col["depends_on"], \
        "spec:log-collector must depend on pkg:svc-core@1.0.0"

    # Both conditional deps must be imported verbatim (marker embedded in the dep
    # constraint string) so the resolver can parse the '; when' clause itself.
    con = sqlite3.connect(outputs["db"])
    try:
        rows = {
            (v, d): c
            for (v, d, c) in con.execute(
                "SELECT version, dep, ver_constraint FROM package_deps WHERE package='svc-core'"
            ).fetchall()
        }
    finally:
        con.close()
    assert rows[("1.0.0", "addon-x")] == ">=1.0.0 ; when curl ==7.80.0"
    assert rows[("1.0.0", "addon-y")] == ">=1.0.0 ; when curl ==8.5.0"


def test_marker_backtrack_feedback(outputs):
    """A conditional dependency's own activation can create a conflict that
    forces the marker package itself to back off, which then flips which OTHER
    conditional dependency on that same marker becomes active.

    media-service requires gate-svc (releases 1.0.0, 2.0.0; no deps or
    conflicts of its own) and beacon (single release 1.0.0), whose two deps
    are both gated on gate-svc:

      'helper-a >=1.0.0 ; when gate-svc ==2.0.0'
      'helper-b >=1.0.0 ; when gate-svc ==1.0.0'

    helper-a's own release declares an UNCONDITIONAL conflict against
    'gate-svc >=2.0.0'. A resolver that picks gate-svc's highest release
    (2.0.0) first, without feeding the conditionally-activated helper-a's own
    conflicts back into gate-svc's version choice, would accept a
    self-contradicting closure: gate-svc@2.0.0 activates beacon's dep on
    helper-a, but helper-a directly forbids gate-svc@2.0.0. The resolver must
    back gate-svc off to 1.0.0, at which point beacon's dep on helper-a goes
    dormant (must not appear anywhere) and its dep on helper-b becomes active
    instead (must be a real node with an edge from beacon)."""
    plan = outputs["plan"]
    selected = {n["name"]: n["version"] for n in plan["build_order"] if n["type"] == "package"}
    by_id = {n["id"]: n for n in plan["build_order"]}
    node_ids = {n["id"] for n in plan["build_order"]}
    all_deps = {d for n in plan["build_order"] for d in n["depends_on"]}

    assert selected.get("gate-svc") == "1.0.0", (
        "gate-svc must back off to 1.0.0: staying at 2.0.0 would activate "
        "beacon's dep on helper-a, but helper-a's own conflict forbids "
        "gate-svc >=2.0.0, making 2.0.0 self-contradicting"
    )
    assert selected.get("beacon") == "1.0.0"

    # Flipped-active branch: helper-b must be a real node with an edge from beacon.
    assert selected.get("helper-b") == "1.0.0", (
        "helper-b must be selected: beacon's conditional dep on it "
        "('; when gate-svc ==1.0.0') is ACTIVE since gate-svc backs off to 1.0.0"
    )
    beacon = by_id.get("pkg:beacon@1.0.0")
    assert beacon is not None, "pkg:beacon@1.0.0 must be in the plan"
    assert beacon["depends_on"] == ["pkg:helper-b@1.0.0"], (
        "beacon must depend on exactly pkg:helper-b@1.0.0: the helper-b edge is "
        "active, and the helper-a edge is dormant and must not be drawn"
    )

    # Dormant branch: helper-a must not appear anywhere, under any version.
    assert "helper-a" not in selected, (
        "helper-a must not be selected: beacon's conditional dep on it "
        "('; when gate-svc ==2.0.0') stays DORMANT since gate-svc is 1.0.0, not 2.0.0"
    )
    assert not any(nid.startswith("pkg:helper-a@") for nid in node_ids), \
        "helper-a must not appear as a node under any version"
    assert not any(d.startswith("pkg:helper-a@") for d in all_deps), \
        "no node may depend on helper-a; its only dependency edge is dormant"

    # media-service must depend on both new root packages.
    media = by_id.get("spec:media-service")
    assert media is not None, "spec:media-service must be in the plan"
    assert "pkg:gate-svc@1.0.0" in media["depends_on"]
    assert "pkg:beacon@1.0.0" in media["depends_on"]

    # Both conditional deps and the unconditional conflict must be imported
    # verbatim so the resolver can parse them itself.
    con = sqlite3.connect(outputs["db"])
    try:
        dep_rows = {
            (v, d): c
            for (v, d, c) in con.execute(
                "SELECT version, dep, ver_constraint FROM package_deps WHERE package='beacon'"
            ).fetchall()
        }
        conf_rows = {
            (v, cf): c
            for (v, cf, c) in con.execute(
                "SELECT version, conflict, ver_constraint FROM package_conflicts WHERE package='helper-a'"
            ).fetchall()
        }
    finally:
        con.close()
    assert dep_rows[("1.0.0", "helper-a")] == ">=1.0.0 ; when gate-svc ==2.0.0"
    assert dep_rows[("1.0.0", "helper-b")] == ">=1.0.0 ; when gate-svc ==1.0.0"
    assert conf_rows[("1.0.0", "gate-svc")] == ">=2.0.0"


def test_transitive_marker_conflict_chain(outputs):
    """A conditional dependency's activation can create a conflict that lives
    ONE HOP BENEATH the marker's direct target, not on the target itself —
    the resolver must still feed it back into the marker package's own
    version choice.

    auth-relay requires netpivot (releases 1.0.0, 2.0.0; no deps or conflicts
    of its own) and relaymgr (single release 1.0.0), whose two deps are both
    gated on netpivot:

      'probe-x >=1.0.0 ; when netpivot ==2.0.0'
      'probe-y >=1.0.0 ; when netpivot ==1.0.0'

    Unlike beacon/helper-a (where the feedback conflict sits directly on the
    marker's own target), probe-x's release carries no conflict at all —
    instead it declares an UNCONDITIONAL dep on linkmod, and linkmod's single
    release carries an UNCONDITIONAL conflict against 'netpivot >=2.0.0'. A
    resolver that picks netpivot's highest release (2.0.0) first, without
    tracing the conflict through probe-x's own dependency to linkmod, would
    accept a self-contradicting closure: netpivot@2.0.0 activates relaymgr's
    dep on probe-x, which unconditionally requires linkmod, but linkmod
    directly forbids netpivot@2.0.0. The resolver must back netpivot off to
    1.0.0, at which point relaymgr's dep on probe-x goes dormant (neither
    probe-x nor linkmod may appear anywhere) and its dep on probe-y becomes
    active instead (must be a real node with an edge from relaymgr)."""
    plan = outputs["plan"]
    selected = {n["name"]: n["version"] for n in plan["build_order"] if n["type"] == "package"}
    by_id = {n["id"]: n for n in plan["build_order"]}
    node_ids = {n["id"] for n in plan["build_order"]}
    all_deps = {d for n in plan["build_order"] for d in n["depends_on"]}

    assert selected.get("netpivot") == "1.0.0", (
        "netpivot must back off to 1.0.0: staying at 2.0.0 would activate "
        "relaymgr's dep on probe-x, whose own unconditional dep on linkmod "
        "conflicts with netpivot >=2.0.0, making 2.0.0 self-contradicting"
    )
    assert selected.get("relaymgr") == "1.0.0"

    # Flipped-active branch: probe-y must be a real node with an edge from relaymgr.
    assert selected.get("probe-y") == "1.0.0", (
        "probe-y must be selected: relaymgr's conditional dep on it "
        "('; when netpivot ==1.0.0') is ACTIVE since netpivot backs off to 1.0.0"
    )
    relaymgr = by_id.get("pkg:relaymgr@1.0.0")
    assert relaymgr is not None, "pkg:relaymgr@1.0.0 must be in the plan"
    assert relaymgr["depends_on"] == ["pkg:probe-y@1.0.0"], (
        "relaymgr must depend on exactly pkg:probe-y@1.0.0: the probe-y edge is "
        "active, and the probe-x edge is dormant and must not be drawn"
    )

    # Dormant branch: probe-x and its own dep linkmod must not appear anywhere.
    assert "probe-x" not in selected, (
        "probe-x must not be selected: relaymgr's conditional dep on it "
        "('; when netpivot ==2.0.0') stays DORMANT since netpivot is 1.0.0, not 2.0.0"
    )
    assert "linkmod" not in selected, (
        "linkmod must not be selected: it is only reachable through probe-x, "
        "whose own incoming edge is dormant"
    )
    assert not any(nid.startswith("pkg:probe-x@") for nid in node_ids), \
        "probe-x must not appear as a node under any version"
    assert not any(nid.startswith("pkg:linkmod@") for nid in node_ids), \
        "linkmod must not appear as a node under any version"
    assert not any(d.startswith("pkg:probe-x@") for d in all_deps), \
        "no node may depend on probe-x; its only dependency edge is dormant"
    assert not any(d.startswith("pkg:linkmod@") for d in all_deps), \
        "no node may depend on linkmod; it is only reachable through probe-x"

    # auth-relay must depend on both new root packages.
    auth_relay = by_id.get("spec:auth-relay")
    assert auth_relay is not None, "spec:auth-relay must be in the plan"
    assert "pkg:netpivot@1.0.0" in auth_relay["depends_on"]
    assert "pkg:relaymgr@1.0.0" in auth_relay["depends_on"]

    # Both conditional deps, probe-x's own unconditional dep, and linkmod's
    # unconditional conflict must be imported verbatim so the resolver can
    # parse them itself rather than special-case a hardcoded pattern.
    con = sqlite3.connect(outputs["db"])
    try:
        relay_deps = {
            (v, d): c
            for (v, d, c) in con.execute(
                "SELECT version, dep, ver_constraint FROM package_deps WHERE package='relaymgr'"
            ).fetchall()
        }
        probe_x_deps = {
            (v, d): c
            for (v, d, c) in con.execute(
                "SELECT version, dep, ver_constraint FROM package_deps WHERE package='probe-x'"
            ).fetchall()
        }
        linkmod_conf = {
            (v, cf): c
            for (v, cf, c) in con.execute(
                "SELECT version, conflict, ver_constraint FROM package_conflicts WHERE package='linkmod'"
            ).fetchall()
        }
    finally:
        con.close()
    assert relay_deps[("1.0.0", "probe-x")] == ">=1.0.0 ; when netpivot ==2.0.0"
    assert relay_deps[("1.0.0", "probe-y")] == ">=1.0.0 ; when netpivot ==1.0.0"
    assert probe_x_deps[("1.0.0", "linkmod")] == ">=1.0.0", (
        "probe-x's dep on linkmod must be UNCONDITIONAL (no marker) — it applies "
        "whenever probe-x itself is reached, regardless of netpivot's version"
    )
    assert linkmod_conf[("1.0.0", "netpivot")] == ">=2.0.0", (
        "linkmod's conflict against netpivot must be UNCONDITIONAL (no marker) — "
        "it is what forces netpivot's backtrack, one hop beneath the marker itself"
    )


def test_deep_cascade_backtrack(outputs):
    """A conflict between an alphabetically-early package and an
    alphabetically-late one must force a full backtrack across the entire
    intervening search, not just a local adjacency check.

    The edge-infra spec pulls in abi-shim (releases 1.0.0, 2.0.0; no deps of its
    own) and zvfs (a SINGLE release, 1.0.0, whose only conflict forbids
    'abi-shim >=2.0.0'). The resolver assigns packages in ascending name order,
    so abi-shim ('abi-shim...') is assigned before nearly every other package in
    the closure, and zvfs ('zvfs...') is assigned after all of them. A resolver
    greedily takes abi-shim@2.0.0 first (highest preferred) since nothing about
    abi-shim alone rules it out; the conflict is only discovered once the search
    reaches zvfs, which has no alternate release to fall back to. The only way to
    satisfy both is to re-open abi-shim's choice and drop it to 1.0.0, which means
    the failure at zvfs must propagate all the way back through every package
    assigned in between (a solver that shortcuts backtracking or only rechecks
    adjacent packages leaves abi-shim at 2.0.0 and either wrongly accepts zvfs
    anyway or fails the whole resolution outright)."""
    plan = outputs["plan"]
    selected = {n["name"]: n["version"] for n in plan["build_order"] if n["type"] == "package"}
    by_id = {n["id"]: n for n in plan["build_order"]}
    order = [n["id"] for n in plan["build_order"]]

    assert selected.get("abi-shim") == "1.0.0", (
        "abi-shim must back off to 1.0.0: zvfs@1.0.0 (its only release) conflicts "
        "with abi-shim >=2.0.0, and that conflict is only discoverable once the "
        "search reaches zvfs at the far end of the assignment order"
    )
    assert selected.get("zvfs") == "1.0.0", "zvfs must be selected at its only release"

    edge = by_id.get("spec:edge-infra")
    assert edge is not None, "spec:edge-infra must be in the plan"
    assert "pkg:abi-shim@1.0.0" in edge["depends_on"]
    assert "pkg:zvfs@1.0.0" in edge["depends_on"]
    assert "pkg:abi-shim@2.0.0" not in [n["id"] for n in plan["build_order"]], (
        "abi-shim@2.0.0 must not appear anywhere in the plan"
    )

    # abi-shim sorts before every other package in the closure; zvfs after all of
    # them - confirming this is a genuinely deep (near-whole-closure) backtrack.
    pkg_ids = [n["id"] for n in plan["build_order"] if n["type"] == "package"]
    assert order.index("pkg:abi-shim@1.0.0") == 0, "abi-shim must be the first package assigned"
    assert order.index("pkg:zvfs@1.0.0") == len(pkg_ids) - 1, "zvfs must be the last package assigned"

    con = sqlite3.connect(outputs["db"])
    try:
        rows = {
            (p, v, cf): c
            for (p, v, cf, c) in con.execute(
                "SELECT package, version, conflict, ver_constraint FROM package_conflicts "
                "WHERE package = 'zvfs'"
            ).fetchall()
        }
    finally:
        con.close()
    assert rows[("zvfs", "1.0.0", "abi-shim")] == ">=2.0.0"


def test_node_ids_encode_version(outputs):
    """Package/toolchain node ids embed the selected version; specs do not."""
    plan = outputs["plan"]
    for n in plan["build_order"]:
        if n["type"] == "package":
            assert n["id"] == f"pkg:{n['name']}@{n['version']}"
        elif n["type"] == "toolchain":
            assert n["id"] == f"tc:{n['name']}@{n['version']}"
        else:
            assert n["id"] == f"spec:{n['name']}"
            assert n["version"] == ""


def test_depends_on_sorted_and_valid(outputs):
    """depends_on lists are ascending-sorted and reference existing nodes."""
    plan = outputs["plan"]
    ids = {n["id"] for n in plan["build_order"]}
    for n in plan["build_order"]:
        assert n["depends_on"] == sorted(n["depends_on"]), f"{n['id']} deps unsorted"
        for d in n["depends_on"]:
            assert d in ids, f"{n['id']} depends on unknown {d}"


def test_edges_reflect_selected_versions(outputs):
    """Dependency edges must point at the resolved release of each dependency."""
    plan = outputs["plan"]
    by_id = {n["id"]: n for n in plan["build_order"]}
    curl = by_id["pkg:curl@7.80.0"]
    assert "pkg:libssl@1.1.1" in curl["depends_on"]
    assert "pkg:libssl@3.0.2" not in curl["depends_on"]
    libxml2 = by_id["pkg:libxml2@2.9.14"]
    assert "pkg:libpng@1.6.37" in libxml2["depends_on"]
    arrow = by_id["pkg:arrow@12.0.0"]
    assert "pkg:boost@1.80.0" in arrow["depends_on"]
    assert "pkg:boost@1.85.0" not in arrow["depends_on"]
    boost = by_id["pkg:boost@1.80.0"]
    assert "pkg:icu@70.1" in boost["depends_on"]
    imaging = by_id["pkg:imaging@4.0.0"]
    assert "pkg:libwebp@1.2.4" in imaging["depends_on"]
    assert "pkg:libwebp@1.3.2" not in imaging["depends_on"]
    libwebp = by_id["pkg:libwebp@1.2.4"]
    assert "pkg:libjpeg-turbo@3.0.1" in libwebp["depends_on"]
    indexer = by_id["pkg:indexer@1.0.0"]
    assert "pkg:tokenizer@3.2.0" in indexer["depends_on"]
    assert "pkg:tokenizer@1.5.0" not in indexer["depends_on"]
    collector = by_id["pkg:collector@1.0.0"]
    assert "pkg:analyzer@1.5.0" in collector["depends_on"]
    assert "pkg:analyzer@4.1.0" not in collector["depends_on"]
    grpc = by_id["pkg:grpc@1.60.0"]
    assert "pkg:protobuf@3.21.3" in grpc["depends_on"]
    assert "pkg:protobuf@4.0.0" not in grpc["depends_on"]
    rpc_gw = by_id["spec:rpc-gateway"]
    assert "pkg:capnproto@0.11.0" in rpc_gw["depends_on"], \
        "rpc-gateway must depend on capnproto@0.11.0 (highest integer-ordered version)"
    assert "pkg:capnproto@0.9.0" not in rpc_gw["depends_on"]
    batch = by_id["spec:batch-worker"]
    assert "pkg:murmur3@3.1.0" in batch["depends_on"], \
        "batch-worker must depend on the resolved hash-lib provider murmur3@3.1.0"
    assert "pkg:xxhash@4.0.0" not in batch["depends_on"], \
        "xxhash@4.0.0 rejected (dep zlib>=1.3.0 infeasible)"
    assert "pkg:xxhash@3.5.0" not in batch["depends_on"], \
        "xxhash@3.5.0 rejected (conflict libssl<2.0.0 fires)"
    # Package extras: search-service requests indexer with extras=['fast','cache'].
    # indexer@1.0.0 must have edges to its two extra deps simd-lib@3.0.0 (fast)
    # and lru-cache@1.5.0 (cache), in addition to its regular dep tokenizer@3.2.0.
    indexer = by_id["pkg:indexer@1.0.0"]
    assert "pkg:simd-lib@3.0.0" in indexer["depends_on"], \
        "indexer must depend on simd-lib@3.0.0 (extras[fast]: simd-lib>=2.0.0)"
    assert "pkg:lru-cache@1.5.0" in indexer["depends_on"], \
        "indexer must depend on lru-cache@1.5.0 (extras[cache]: lru-cache>=1.0.0, backed off from 2.0.0)"
    assert "pkg:lru-cache@2.0.0" not in indexer["depends_on"], \
        "lru-cache@2.0.0 conflicts with tokenizer<4.0.0 (tokenizer=3.2.0)"
    # Transitive extra: the extra dep simd-lib@3.0.0 has its own dep vecmath>=4.0,
    # so simd-lib must carry an edge to the resolved vecmath@4.2.0.
    simd = by_id["pkg:simd-lib@3.0.0"]
    assert "pkg:vecmath@4.2.0" in simd["depends_on"], \
        "simd-lib@3.0.0 must depend on vecmath@4.2.0 (transitive extra dep)"
    assert "pkg:vecmath@5.0.0" not in simd["depends_on"], \
        "vecmath@5.0.0 rejected (dep cpuflags>=2.0 infeasible)"
    assert "pkg:vecmath@4.5.0" not in simd["depends_on"], \
        "vecmath@4.5.0 rejected (conflict libssl<2.0.0 fires)"


def test_disjunctive_constraint_resolution(outputs):
    """Disjunctive ('|') and conjunctive (',') constraints must be parsed and
    solved. indexer 2.0.0 needs tokenizer>=5.0.0 but telemetry caps
    tokenizer<4.0.0, so indexer backs off to 1.0.0 whose dep is two OR-groups
    '>=1.0.0,<2.0.0 | >=3.0.0,<4.0.0'; the highest tokenizer under <4.0.0 is
    3.2.0 (the SECOND group binds). collector 2.0.0 needs analyzer>=4.0.0 but
    telemetry caps analyzer<3.0.0, so collector backs off to 1.0.0 whose dep is
    '>=1.0.0,<2.0.0 | >=4.0.0'; the >=4.0.0 group is empty under <3.0.0, so the
    FIRST group binds and analyzer resolves to 1.5.0. re2 carries a pure comma
    conjunction '>=2.0.0,<2.5.0', so it resolves to 2.3.0 not the higher 2.7.0.
    A resolver that reads only one group of a '|', or ignores a comma-ANDed
    bound, picks the wrong release for at least one of these."""
    plan = outputs["plan"]
    selected = {n["name"]: n["version"] for n in plan["build_order"] if n["type"] == "package"}
    assert selected["indexer"] == "1.0.0", "indexer 2.0.0 needs tokenizer>=5.0.0, forbidden by tokenizer<4.0.0"
    assert selected["tokenizer"] == "3.2.0", "second OR-group >=3.0.0,<4.0.0 binds under tokenizer<4.0.0"
    assert selected["collector"] == "1.0.0", "collector 2.0.0 needs analyzer>=4.0.0, forbidden by analyzer<3.0.0"
    assert selected["analyzer"] == "1.5.0", "first OR-group >=1.0.0,<2.0.0 binds; >=4.0.0 group is empty under <3.0.0"
    assert selected["re2"] == "2.3.0", "comma conjunction >=2.0.0,<2.5.0 excludes 2.7.0"


def test_compatible_release_constraint_resolution(outputs):
    """The '~=' (compatible release) operator bounds versions to the same
    major component. '~= X.Y' means >=X.Y.0 and <(X+1).0.0. rpc-gateway
    requires protobuf ~= 3.20 (i.e. >=3.20.0, <4.0.0). grpc 2.0.0 needs
    protobuf ~= 4.0 (>=4.0.0, <5.0.0); combined with the spec's upper bound
    <4.0.0 there is no protobuf release that satisfies both, so grpc backs off
    to 1.60.0 (which also needs protobuf ~= 3.20). The highest protobuf in
    [3.20.0, 4.0.0) is 3.21.3. A resolver that treats '~=' as plain '>='
    picks grpc 2.0.0 with protobuf 4.0.0, violating the spec's upper bound."""
    plan = outputs["plan"]
    selected = {n["name"]: n["version"] for n in plan["build_order"] if n["type"] == "package"}
    assert selected["grpc"] == "1.60.0", \
        "grpc 2.0.0 needs protobuf ~= 4.0 (>=4.0), but rpc-gateway caps protobuf ~= 3.20 (<4.0)"
    assert selected["protobuf"] == "3.21.3", \
        "highest protobuf in ~= 3.20 window [3.20.0, 4.0.0) is 3.21.3"


def test_integer_version_comparison(outputs):
    """Version components must be compared as integers, not as strings. The lock
    contains capnproto with releases 0.9.0, 0.10.0, and 0.11.0; the spec requires
    capnproto >=0.9.0 with no further constraints, so the resolver must pick the
    highest available version. Numerically that is 0.11.0 (0 < 9 < 10 < 11 as
    integers). Lexicographically, however, '0.9.0' sorts after '0.10.0' and
    '0.11.0' because the character '9' has a higher ASCII value than '1', so a
    resolver doing string comparison would incorrectly choose 0.9.0. The
    instruction states that version components are compared as integers; this test
    enforces that requirement against a concrete multi-digit-minor version set."""
    plan = outputs["plan"]
    selected = {n["name"]: n["version"] for n in plan["build_order"] if n["type"] == "package"}
    assert "capnproto" in selected, "capnproto must be in the closure (required by rpc-gateway)"
    assert selected["capnproto"] == "0.11.0", (
        "capnproto must resolve to 0.11.0 (highest integer-ordered version); "
        "a resolver using lexicographic string comparison picks 0.9.0 because "
        "'9' > '1' as a character — version components are integers, not strings"
    )


def test_epoch_version_comparison(outputs):
    """Version epochs (PEP 440 '<N>!' prefix) dominate ordinary release-number
    comparison. The stream-engine spec requires codecpad and framebuf. codecpad
    ships three releases: 2.4.0 (epoch 0), 1!1.0.0 and 1!1.2.0 (epoch 1). Because
    the epoch dominates, 1!1.2.0 outranks 1!1.0.0 outranks 2.4.0 even though 2 > 1
    on the plain leading number, so the highest release is 1!1.2.0.

    The choice CASCADES into framebuf: codecpad@1!1.2.0 requires 'framebuf >=3.0.0'
    (resolved to framebuf@3.2.0), whereas the epoch-0 codecpad@2.4.0 requires
    'framebuf >=2.0.0,<3.0.0' (which would pin framebuf at 2.5.0). A resolver that
    compares versions as plain dotted integers — or that fails to parse the '!'
    epoch marker — mis-ranks codecpad, picks 2.4.0, and then pins framebuf at
    2.5.0, getting BOTH nodes wrong. This test enforces epoch-aware comparison and
    the dependent version cascade it drives."""
    plan = outputs["plan"]
    selected = {n["name"]: n["version"] for n in plan["build_order"] if n["type"] == "package"}
    assert "codecpad" in selected, "codecpad must be in the closure (required by stream-engine)"
    assert selected["codecpad"] == "1!1.2.0", (
        "codecpad must resolve to 1!1.2.0 (epoch 1 dominates epoch-0 releases); a "
        "resolver comparing plain dotted integers wrongly picks 2.4.0"
    )
    assert "framebuf" in selected, "framebuf must be in the closure"
    assert selected["framebuf"] == "3.2.0", (
        "framebuf must resolve to 3.2.0: codecpad@1!1.2.0 requires framebuf>=3.0.0. "
        "An epoch-blind resolver picks codecpad@2.4.0 whose framebuf>=2.0.0,<3.0.0 "
        "would instead pin framebuf at 2.5.0"
    )
    # The epoch node id must carry the full version verbatim, including the '!'.
    ids = {n["id"] for n in plan["build_order"]}
    assert "pkg:codecpad@1!1.2.0" in ids, "codecpad node id must preserve the epoch marker"


def test_topological_order(outputs):
    """Every dependency appears before the node that depends on it."""
    plan = outputs["plan"]
    pos = {n["id"]: i for i, n in enumerate(plan["build_order"])}
    for n in plan["build_order"]:
        for d in n["depends_on"]:
            assert pos[d] < pos[n["id"]], f"{d} not before {n['id']}"


def test_spec_ordering_constraints(outputs):
    """Specs that declare 'requires_specs' must depend on the listed specs and
    must appear after them in the build order.

    data-pipeline declares requires_specs: ['search-service'].
      - spec:search-service must appear before spec:data-pipeline in EXPECTED_ORDER.
      - spec:data-pipeline's depends_on must include 'spec:search-service'.
      - Without the constraint data-pipeline would be first (alphabetically 'd'
        comes before 'l','m','r','s','t'), but with it, search-service must come
        first and data-pipeline moves to position 30 in the order (after 'd' <
        't' tie-break with telemetry once search-service is placed).

    web-frontend declares requires_specs: ['api-service'].
      - spec:api-service must appear before spec:web-frontend in EXPECTED_ORDER.
      - spec:web-frontend's depends_on must include 'spec:api-service'.
      - Without the constraint the TC tail was: node-toolchain → web-frontend →
        python-toolchain → api-service (web-frontend and python-toolchain compete;
        'spec:...' < 'tc:...' so web-frontend won).  With the constraint,
        python-toolchain and api-service both precede web-frontend: the tail
        becomes node-toolchain → python-toolchain → api-service → web-frontend.

    The spec_ordering table in the DB must contain both constraints.
    Implementations that ignore spec_ordering get the wrong build order and the
    wrong edge count (52 vs 50 without it, on top of the 2 extras edges)."""
    plan = outputs["plan"]
    by_id = {n["id"]: n for n in plan["build_order"]}
    order = [n["id"] for n in plan["build_order"]]

    # spec:data-pipeline must depend on spec:search-service
    dp = by_id.get("spec:data-pipeline")
    assert dp is not None, "spec:data-pipeline must be in the plan"
    assert "spec:search-service" in dp["depends_on"], (
        "spec:data-pipeline must have spec:search-service in depends_on "
        "(declared via requires_specs: ['search-service'])"
    )
    # search-service must appear before data-pipeline in build order
    assert order.index("spec:search-service") < order.index("spec:data-pipeline"), (
        "spec:search-service must be placed before spec:data-pipeline "
        "because data-pipeline has a spec-ordering constraint on search-service"
    )

    # spec:web-frontend must depend on spec:api-service
    wf = by_id.get("spec:web-frontend")
    assert wf is not None, "spec:web-frontend must be in the plan"
    assert "spec:api-service" in wf["depends_on"], (
        "spec:web-frontend must have spec:api-service in depends_on "
        "(declared via requires_specs: ['api-service'])"
    )
    # api-service must appear before web-frontend in build order
    assert order.index("spec:api-service") < order.index("spec:web-frontend"), (
        "spec:api-service must be placed before spec:web-frontend "
        "because web-frontend has a spec-ordering constraint on api-service"
    )

    # The spec_ordering table in the DB must be populated
    con = sqlite3.connect(outputs["db"])
    try:
        rows = con.execute(
            "SELECT spec, required_spec FROM spec_ordering ORDER BY spec, required_spec"
        ).fetchall()
    finally:
        con.close()
    ordering_pairs = {(r[0], r[1]) for r in rows}
    assert ("data-pipeline", "search-service") in ordering_pairs, (
        "spec_ordering must contain (data-pipeline, search-service)"
    )
    assert ("web-frontend", "api-service") in ordering_pairs, (
        "spec_ordering must contain (web-frontend, api-service)"
    )


def test_exact_build_order(outputs):
    """The deterministic tie-break produces exactly this build order."""
    plan = outputs["plan"]
    order = [n["id"] for n in plan["build_order"]]
    assert order == EXPECTED_ORDER


def test_plan_deterministic(outputs):
    """Re-running the full pipeline yields byte-identical plan output."""
    tmp = tempfile.mkdtemp()
    try:
        _, plan_a, _ = run_pipeline(os.path.join(tmp, "a"))
        _, plan_b, _ = run_pipeline(os.path.join(tmp, "b"))
        with open(plan_a, "rb") as f:
            a = f.read()
        with open(plan_b, "rb") as f:
            b = f.read()
        assert a == b
        with open(outputs["plan_path"], "rb") as f:
            assert f.read() == a
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_dot_nodes_match_plan(outputs):
    """Graph nodes equal plan nodes, with matching type attributes."""
    plan = outputs["plan"]
    nodes, _ = parse_dot(outputs["dot"])
    plan_types = {n["id"]: n["type"] for n in plan["build_order"]}
    assert nodes == plan_types


def test_dot_edges_match_plan(outputs):
    """Graph edges equal the dependency edges from the plan."""
    plan = outputs["plan"]
    _, edges = parse_dot(outputs["dot"])
    expected = set()
    for n in plan["build_order"]:
        for d in n["depends_on"]:
            expected.add((n["id"], d))
    assert edges == expected
    assert len(edges) == EXPECTED_EDGE_COUNT


def test_dot_edges_sorted(outputs):
    """DOT edge lines are emitted in (source, target) ascending order."""
    edge_lines = [ln for ln in outputs["dot"].splitlines() if "->" in ln]
    pairs = []
    edge_re = re.compile(r'^\s*"([^"]+)"\s*->\s*"([^"]+)"\s*;\s*$')
    for ln in edge_lines:
        m = edge_re.match(ln)
        assert m, f"malformed edge line: {ln}"
        pairs.append((m.group(1), m.group(2)))
    assert pairs == sorted(pairs)


def test_dot_deterministic(outputs):
    """Re-running graph yields byte-identical DOT output."""
    tmp = tempfile.mkdtemp()
    try:
        _, _, dot_a = run_pipeline(os.path.join(tmp, "a"))
        _, _, dot_b = run_pipeline(os.path.join(tmp, "b"))
        with open(dot_a) as f:
            a = f.read()
        with open(dot_b) as f:
            b = f.read()
        assert a == b
        assert outputs["dot"] == a
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_plan_and_graph_use_only_the_db(outputs):
    """plan and graph must resolve from the SQLite DB alone. We import while the
    fixtures exist, then move the entire /app/data fixture tree out of the way and
    run plan and graph from only the DB. graph runs first, in a directory where no
    build-plan file exists, so an implementation cannot pass by re-reading the
    fixture JSON or a previously written plan. The outputs must still be correct."""
    work = tempfile.mkdtemp()
    plan_text = dot_text = None
    backup = os.path.join(work, "data_backup")
    try:
        db = os.path.join(work, "build.db")
        subprocess.run(
            [DEPMAP, "import", "--specs", SPECS, "--locks", LOCKS,
             "--toolchains", TOOLCHAINS, "--db", db],
            check=True, capture_output=True, text=True,
        )
        assert os.path.exists("/app/data"), "fixtures missing before hide"
        # Remove the fixture tree entirely (keeping a backup to restore after).
        shutil.copytree("/app/data", backup)
        shutil.rmtree("/app/data")
        try:
            assert not os.path.exists(SPECS), "fixtures should be removed"
            graph_dir = os.path.join(work, "graph_only")
            plan_dir = os.path.join(work, "plan_only")
            os.makedirs(graph_dir)
            os.makedirs(plan_dir)
            dot_path = os.path.join(graph_dir, "depgraph.dot")
            plan_path = os.path.join(plan_dir, "build-plan.json")
            # graph runs in a clean dir with NO build-plan file present.
            assert not os.path.exists(os.path.join(graph_dir, "build-plan.json"))
            subprocess.run([DEPMAP, "graph", "--db", db, "--out", dot_path],
                           check=True, capture_output=True, text=True)
            subprocess.run([DEPMAP, "plan", "--db", db, "--out", plan_path],
                           check=True, capture_output=True, text=True)
            with open(plan_path) as f:
                plan_text = f.read()
            with open(dot_path) as f:
                dot_text = f.read()
        finally:
            if not os.path.exists("/app/data"):
                shutil.copytree(backup, "/app/data")
    finally:
        if not os.path.exists("/app/data") and os.path.exists(backup):
            shutil.copytree(backup, "/app/data")
        shutil.rmtree(work, ignore_errors=True)
    # Results computed from the DB alone must match the canonical fixtured run.
    assert json.loads(plan_text) == outputs["plan"], "plan differs without fixtures"
    assert dot_text == outputs["dot"], "graph differs without fixtures"


def test_virtual_package_provider_resolution(outputs):
    """Virtual package deps (names that appear in spec_packages but not in the
    packages table) must be resolved to a real provider via the package_provides
    table. The log-collector spec requires 'compress-lib >=1.3'. Three candidates:
    lz4@2.0.0 provides compress-lib@2.0 (satisfies >=1.3) but its conflict
    'libssl<3.0.0' is triggered by the chosen libssl@1.1.1 — rejected. lz4@1.9.4
    provides compress-lib@1.0 which is below 1.3 — rejected by the constraint.
    zstd@1.5.5 provides compress-lib@1.5 (>=1.3, no conflicts) — chosen. A solver
    that picks the first satisfying candidate or ignores provider conflicts gets
    this wrong."""
    plan = outputs["plan"]
    selected = {n["name"]: n["version"] for n in plan["build_order"] if n["type"] == "package"}
    by_id = {n["id"]: n for n in plan["build_order"]}

    assert "zstd" in selected, "zstd must be in the plan as the virtual dep provider"
    assert selected["zstd"] == "1.5.5", \
        "zstd@1.5.5 provides compress-lib@1.5 (>=1.3) with no conflicts"
    assert "lz4" not in selected, (
        "lz4 must not be selected: 1.9.4 provides compress-lib@1.0 (<1.3); "
        "2.0.0 provides 2.0 (>=1.3) but conflicts with the chosen libssl@1.1.1 (<3.0.0)"
    )

    log_col = by_id.get("spec:log-collector")
    assert log_col is not None, "spec:log-collector must be in the plan"
    assert "pkg:zstd@1.5.5" in log_col["depends_on"], \
        "log-collector must depend on pkg:zstd@1.5.5 (resolved provider for compress-lib >=1.3)"

    # Verify the package_provides DB table was populated
    con = sqlite3.connect(outputs["db"])
    try:
        rows = con.execute(
            "SELECT package, version, virtual, provided_version "
            "FROM package_provides ORDER BY package, version"
        ).fetchall()
    finally:
        con.close()
    provider_map = {(r[0], r[1]): (r[2], r[3]) for r in rows}
    assert len(provider_map) >= 3, \
        "package_provides must have rows for lz4@1.9.4, lz4@2.0.0, and zstd@1.5.5"
    assert ("zstd", "1.5.5") in provider_map, "zstd@1.5.5 must be in package_provides"
    assert provider_map[("zstd", "1.5.5")] == ("compress-lib", "1.5"), \
        "zstd@1.5.5 provides compress-lib at version 1.5"
    assert ("lz4", "1.9.4") in provider_map, "lz4@1.9.4 must be in package_provides"
    assert ("lz4", "2.0.0") in provider_map, "lz4@2.0.0 must be in package_provides"


def test_provider_with_infeasible_deps_rejected(outputs):
    """A virtual provider candidate whose own dep constraints are violated by the
    current package selection must be skipped, even if its provided version is the
    highest. batch-worker requires 'hash-lib >=3.0'. Candidates in descending
    provided-version order:
    1. xxhash@4.0.0 provides hash-lib@4.0 (satisfies >=3.0) but has dep
       'zlib >=1.3.0'; the chosen zlib is 1.2.13 which does NOT satisfy >=1.3.0
       → REJECTED on infeasible dep.
    2. xxhash@3.5.0 provides hash-lib@3.5 (satisfies >=3.0) but conflicts with
       'libssl <2.0.0'; the chosen libssl is 1.1.1 which satisfies <2.0.0
       → REJECTED on conflict.
    3. murmur3@3.1.0 provides hash-lib@3.1 (satisfies >=3.0), no deps, no
       conflicts → CHOSEN.
    A resolver that picks the highest-provided-version candidate without verifying
    dep feasibility will select xxhash@4.0.0 and produce an invalid plan."""
    plan = outputs["plan"]
    selected = {n["name"]: n["version"] for n in plan["build_order"] if n["type"] == "package"}
    pkg_names = {n["name"] for n in plan["build_order"] if n["type"] == "package"}
    by_id = {n["id"]: n for n in plan["build_order"]}

    assert "murmur3" in selected, \
        "murmur3 must be chosen as the hash-lib provider for batch-worker"
    assert selected["murmur3"] == "3.1.0", \
        "murmur3@3.1.0 is the first valid candidate after xxhash rejections"
    assert "xxhash" not in pkg_names, (
        "xxhash must not appear in the closure: "
        "4.0.0 rejected (dep zlib>=1.3.0 infeasible since zlib=1.2.13<1.3.0); "
        "3.5.0 rejected (conflict libssl<2.0.0 triggers since libssl=1.1.1<2.0.0)"
    )
    batch = by_id.get("spec:batch-worker")
    assert batch is not None, "spec:batch-worker must be in the plan"
    assert "pkg:murmur3@3.1.0" in batch["depends_on"], \
        "batch-worker must have a direct dep on the resolved hash-lib provider"
    assert "pkg:xxhash@4.0.0" not in batch["depends_on"], \
        "xxhash@4.0.0 is not a valid provider"
    assert "pkg:xxhash@3.5.0" not in batch["depends_on"], \
        "xxhash@3.5.0 is not a valid provider"

    # Verify xxhash and murmur3 entries exist in package_provides
    con = sqlite3.connect(outputs["db"])
    try:
        prov_rows = con.execute(
            "SELECT package, version, virtual, provided_version "
            "FROM package_provides WHERE virtual='hash-lib' ORDER BY package, version"
        ).fetchall()
    finally:
        con.close()
    prov = {(r[0], r[1]): r[3] for r in prov_rows}
    assert ("murmur3", "3.1.0") in prov, \
        "murmur3@3.1.0 must be in package_provides"
    assert prov[("murmur3", "3.1.0")] == "3.1", \
        "murmur3@3.1.0 provides hash-lib at version 3.1"
    assert ("xxhash", "3.5.0") in prov, \
        "xxhash@3.5.0 must be in package_provides (imported but not chosen)"
    assert ("xxhash", "4.0.0") in prov, \
        "xxhash@4.0.0 must be in package_provides (imported but not chosen)"


def test_extras_resolution(outputs):
    """Package extras: search-service requests indexer with extras=['fast','cache'].
    indexer@1.0.0 must pull in simd-lib (from the 'fast' extra, simd-lib>=2.0.0 →
    simd-lib@3.0.0 chosen as highest satisfying release) and lru-cache (from the
    'cache' extra, lru-cache>=1.0.0 → lru-cache@2.0.0 is highest but it conflicts
    with tokenizer<4.0.0 because tokenizer=3.2.0 < 4.0.0, so it backs off to
    lru-cache@1.5.0). An implementation that ignores the extras field of spec
    packages will produce only 38 nodes (missing simd-lib and lru-cache) and will
    fail test_node_and_edge_counts and test_closure_packages_exact. An implementation
    that picks lru-cache@2.0.0 will fail on the conflict check.
    The package_extras table must be populated with the per-release extra dep entries."""
    plan = outputs["plan"]
    selected = {n["name"]: n["version"] for n in plan["build_order"] if n["type"] == "package"}

    # simd-lib and lru-cache must be in the closure (pulled in via extras)
    assert "simd-lib" in selected, \
        "simd-lib must be in the closure (indexer extras[fast]: simd-lib>=2.0.0)"
    assert selected["simd-lib"] == "3.0.0", \
        "simd-lib@3.0.0 is the highest satisfying simd-lib>=2.0.0"
    assert "lru-cache" in selected, \
        "lru-cache must be in the closure (indexer extras[cache]: lru-cache>=1.0.0)"
    assert selected["lru-cache"] == "1.5.0", (
        "lru-cache@2.0.0 conflicts with tokenizer<4.0.0 (selected tokenizer=3.2.0 < 4.0.0); "
        "must back off to lru-cache@1.5.0"
    )

    # Verify the package_extras table was created and populated
    con = sqlite3.connect(outputs["db"])
    try:
        tables = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "package_extras" in tables, \
            "package_extras table must exist (stores per-release extras deps)"
        # indexer@1.0.0 must have entries in package_extras
        # At minimum, the 'fast' and 'cache' extra entries must be present
        extra_names = {r[0] for r in con.execute(
            "SELECT extra_name FROM package_extras "
            "WHERE package='indexer' AND version='1.0.0'"
        ).fetchall()}
        assert "fast" in extra_names, \
            "package_extras must have 'fast' extra for indexer@1.0.0"
        assert "cache" in extra_names, \
            "package_extras must have 'cache' extra for indexer@1.0.0"
    finally:
        con.close()


def test_transitive_extras_backtracking(outputs):
    """Extras carry a full transitive sub-closure, not flat leaves. The extra
    package simd-lib@3.0.0 (pulled in by indexer[fast]) itself declares
    'vecmath >=4.0', so vecmath joins the closure and is resolved by the same
    highest-version / conflict / feasible-dep rules used for regular deps:
      vecmath@5.0.0 provides no conflicts but its dep 'cpuflags >=2.0' is
        infeasible (cpuflags only ships 1.2.0 < 2.0) → rejected on infeasible dep.
      vecmath@4.5.0 conflicts with 'libssl <2.0.0'; the chosen libssl=1.1.1
        satisfies <2.0.0 → conflict fires → rejected.
      vecmath@4.2.0 has no deps and no triggered conflicts → CHOSEN.
    An implementation that treats extras as flat leaves never expands simd-lib's
    own dependency, so it produces 40 nodes / 52 edges instead of 41 / 53 and omits
    the pkg:simd-lib@3.0.0 -> pkg:vecmath@4.2.0 edge. cpuflags is imported but never
    selected because its only referrer (vecmath@5.0.0) is rejected."""
    plan = outputs["plan"]
    selected = {n["name"]: n["version"] for n in plan["build_order"] if n["type"] == "package"}
    pkg_names = set(selected)
    by_id = {n["id"]: n for n in plan["build_order"]}
    order = [n["id"] for n in plan["build_order"]]

    assert "vecmath" in selected, \
        "vecmath must be in the closure (transitive dep of simd-lib@3.0.0)"
    assert selected["vecmath"] == "4.2.0", (
        "vecmath must resolve to 4.2.0: 5.0.0 rejected (dep cpuflags>=2.0 infeasible), "
        "4.5.0 rejected (conflict libssl<2.0.0 fires)"
    )
    assert "cpuflags" not in pkg_names, \
        "cpuflags must not be selected (only referrer vecmath@5.0.0 is rejected)"

    # simd-lib carries the transitive edge and must be placed after vecmath.
    simd = by_id["pkg:simd-lib@3.0.0"]
    assert "pkg:vecmath@4.2.0" in simd["depends_on"], \
        "simd-lib@3.0.0 must depend on its transitive extra dep vecmath@4.2.0"
    assert order.index("pkg:vecmath@4.2.0") < order.index("pkg:simd-lib@3.0.0"), \
        "vecmath must be built before simd-lib (transitive dependency ordering)"

    # The vecmath deps/conflicts must be present in the DB per-release.
    con = sqlite3.connect(outputs["db"])
    try:
        deps = {(v, d): c for (v, d, c) in con.execute(
            "SELECT version, dep, ver_constraint FROM package_deps WHERE package='vecmath'"
        ).fetchall()}
        simd_deps = {(v, d): c for (v, d, c) in con.execute(
            "SELECT version, dep, ver_constraint FROM package_deps WHERE package='simd-lib'"
        ).fetchall()}
    finally:
        con.close()
    assert simd_deps.get(("3.0.0", "vecmath")) == ">=4.0", \
        "simd-lib@3.0.0 must declare its dep vecmath>=4.0 in package_deps"
    assert deps.get(("5.0.0", "cpuflags")) == ">=2.0", \
        "vecmath@5.0.0's infeasible dep cpuflags>=2.0 must be imported per-release"


def test_release_specific_dep_membership(outputs):
    """A package's closure membership must follow the SELECTED release's own deps,
    not the union of every release's deps. log-collector requires authgate>=1.0.0.
    authgate@1.0.0 (its only release) depends on authtoken>=1.0.0 and conflicts
    with authtoken>=2.0.0. authtoken ships authtoken@2.0.0 (whose own dep is
    'auditlog >=1.0.0') and authtoken@1.5.0 (no deps at all). The solver tries the
    highest release first: authtoken@2.0.0 is rejected because authgate's conflict
    fires against it, so the search backs off to authtoken@1.5.0, which declares no
    deps at all. Because a release's dependency names differ from release to
    release, auditlog — a real dependency of the REJECTED release only — must never
    appear in the output: not as a node, not as an edge target, not anywhere. A
    resolver that computes closure membership from the union of dep names across
    every release of a package (instead of scoping membership to whichever release
    actually got selected) wrongly pulls auditlog in as a phantom, unreferenced
    node that nothing in the real build actually needs."""
    plan = outputs["plan"]
    selected = {n["name"]: n["version"] for n in plan["build_order"] if n["type"] == "package"}
    pkg_names = set(selected)
    node_ids = {n["id"] for n in plan["build_order"]}
    all_deps = {d for n in plan["build_order"] for d in n["depends_on"]}

    assert "authgate" in selected and selected["authgate"] == "1.0.0", \
        "authgate is log-collector's only release and must be selected at 1.0.0"
    assert "authtoken" in selected and selected["authtoken"] == "1.5.0", (
        "authtoken must back off to 1.5.0: authgate conflicts with authtoken>=2.0.0, "
        "so the higher release 2.0.0 is rejected"
    )
    assert "auditlog" not in pkg_names, (
        "auditlog must not be selected: its only referrer authtoken@2.0.0 was "
        "rejected, and the chosen authtoken@1.5.0 has no deps"
    )
    assert not any(nid.startswith("pkg:auditlog@") for nid in node_ids), \
        "auditlog must not appear as a node under any version"
    assert not any(d.startswith("pkg:auditlog@") for d in all_deps), \
        "no node may depend on auditlog; the edge only exists on the rejected release"

    by_id = {n["id"]: n for n in plan["build_order"]}
    authgate = by_id["pkg:authgate@1.0.0"]
    assert authgate["depends_on"] == ["pkg:authtoken@1.5.0"], (
        "authgate must depend on the actually-selected authtoken@1.5.0, with no "
        "auditlog edge leaking in from the rejected 2.0.0 release"
    )

    # Both releases' deps must still be imported per-version in the DB (import is
    # trustworthy and records every release, even the one the resolver rejects).
    con = sqlite3.connect(outputs["db"])
    try:
        deps = {(v, d): c for (v, d, c) in con.execute(
            "SELECT version, dep, ver_constraint FROM package_deps WHERE package='authtoken'"
        ).fetchall()}
        confs = {(v, c): con_ for (v, c, con_) in con.execute(
            "SELECT version, conflict, ver_constraint FROM package_conflicts WHERE package='authgate'"
        ).fetchall()}
    finally:
        con.close()
    assert deps.get(("2.0.0", "auditlog")) == ">=1.0.0", \
        "authtoken@2.0.0's dep on auditlog>=1.0.0 must be imported per-release"
    assert ("1.5.0", "auditlog") not in deps, \
        "authtoken@1.5.0 declares no deps and must not show an auditlog row"
    assert confs.get(("1.0.0", "authtoken")) == ">=2.0.0", \
        "authgate@1.0.0's conflict against authtoken>=2.0.0 must be imported"


def test_dot_header_and_node_order(outputs):
    """The DOT output must be a digraph named depmap and emit its node lines in
    ascending id order, matching the graph contract in the instruction."""
    lines = outputs["dot"].splitlines()
    header = next(ln for ln in lines if ln.strip())
    assert re.match(r'^\s*digraph\s+depmap\s*\{\s*$', header), \
        f"DOT header must declare 'digraph depmap {{', got: {header!r}"
    node_re = re.compile(r'^\s*"([^"]+)"\s*\[type="([^"]+)"\]\s*;\s*$')
    node_ids = []
    for ln in lines:
        m = node_re.match(ln)
        if m:
            node_ids.append(m.group(1))
    assert node_ids, "no node lines found in DOT"
    assert node_ids == sorted(node_ids), "DOT node lines are not in ascending id order"
    plan_ids = sorted(n["id"] for n in outputs["plan"]["build_order"])
    assert node_ids == plan_ids, "DOT node ids do not match the plan nodes"
