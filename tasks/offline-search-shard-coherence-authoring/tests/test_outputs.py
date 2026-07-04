import json
import subprocess
from pathlib import Path

APP = Path("/app")
ENV = APP / "environment"
RUNNER = "/app/environment/scripts/run_search.sh"


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def run_search(plan: Path, out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([RUNNER, str(plan), str(out)], cwd=str(ENV), check=True, text=True, capture_output=True)
    return json.loads(out.read_text(encoding="utf-8"))


def query_at(report, index):
    return report["queries"][index]


def results_at(report, index):
    return query_at(report, index)["results"]


def make_case(tmp_path: Path, *, docs_by_shard, queries, canonical="", robots="", limit=5, stale_entries=None):
    base = tmp_path / "case"
    snap = base / "snapshot"
    (snap / "shards").mkdir(parents=True)
    shards = []
    for shard_id, docs in docs_by_shard.items():
        rel = f"shards/{shard_id}.jsonl"
        write_jsonl(snap / rel, docs)
        shards.append({"id": shard_id, "path": rel})
    (snap / "canonical.tsv").write_text(canonical, encoding="utf-8")
    (snap / "robots.tsv").write_text(robots, encoding="utf-8")
    write_json(
        snap / "manifest.json",
        {
            "snapshot_id": "case-snapshot",
            "freshness_epoch": "2026-05-20",
            "canonical": "canonical.tsv",
            "robots": "robots.tsv",
            "shards": shards,
        },
    )
    write_jsonl(base / "queries.jsonl", queries)
    cache = base / "segment-cache.json"
    write_json(cache, {"schema_version": "segment-cache-v1", "entries": stale_entries or []})
    plan = base / "plan.json"
    write_json(plan, {"manifest": str(snap / "manifest.json"), "queries": str(base / "queries.jsonl"), "cache": str(cache), "limit": limit})
    return plan, base / "out.json", cache, snap


def stale_public_cache():
    return {
        "schema_version": "segment-cache-v1",
        "entries": [
            {
                "snapshot_hash": "sha256:not-current",
                "query_id": "q-solar",
                "query_text": "solar inverter warranty",
                "shard": "news",
                "limit": 3,
                "results": [
                    {
                        "canonical_url": "https://old.example.com/solar-warranty-2024",
                        "selected_url": "https://old.example.com/solar-warranty-2024",
                        "title": "Old solar warranty memo",
                        "score": 99.0,
                        "published": "2024-01-01",
                        "source_shard": "news",
                        "matched_terms": ["solar", "inverter", "warranty"],
                        "supporting_urls": ["https://old.example.com/solar-warranty-2024"],
                    }
                ],
            },
            {
                "snapshot_hash": "sha256:not-current",
                "query_id": "q-reef",
                "query_text": "\"reef lantern\" maintenance",
                "shard": "docs",
                "limit": 3,
                "results": [
                    {
                        "canonical_url": "https://old.example.com/reef-lantern",
                        "selected_url": "https://old.example.com/reef-lantern",
                        "title": "Old reef lantern archive",
                        "score": 77.0,
                        "published": "2024-01-01",
                        "source_shard": "docs",
                        "matched_terms": ["reef", "lantern"],
                        "supporting_urls": ["https://old.example.com/reef-lantern"],
                    }
                ],
            },
        ],
    }


class TestOfflineSearchShardCoherence:
    def test_public_command_ignores_stale_cache_and_collapses_canonicals(self, tmp_path):
        """The visible workflow must regenerate current web-search results instead of trusting plausible stale segments."""
        cache_path = ENV / "state" / "segment-cache.json"
        write_json(cache_path, stale_public_cache())
        report = run_search(ENV / "configs" / "public-plan.json", tmp_path / "public-report.json")
        assert report["schema_version"] == "offline-search-run-v1"
        assert report["snapshot_hash"].startswith("sha256:")
        expected_solar = "https://example.com/solar-inverter-guide"
        expected_reef = "https://coast.example.com/reef-lantern"
        stale_host = "old.example.com"
        mirror_host = "mirror.example.net"
        solar = results_at(report, 0)
        assert solar[0]["canonical_url"] == expected_solar
        assert all(stale_host not in result["canonical_url"] for result in solar)
        assert all(mirror_host not in url for result in solar for url in result["supporting_urls"])
        solar_canonicals = [r["canonical_url"] for r in solar]
        assert len(solar_canonicals) == len(set(solar_canonicals))
        assert expected_solar in solar_canonicals
        reef = results_at(report, 1)
        assert reef[0]["canonical_url"] == expected_reef
        for segment in report["provenance"]["segments"]:
            assert segment["snapshot_hash"] == report["snapshot_hash"]

    def test_cache_key_includes_snapshot_hash_and_query_text(self, tmp_path):
        """Dirty replay with the same query id must recompute when query text or snapshot identity changes."""
        shard_id = "main"
        docs = {
            shard_id: [
                {"url": "https://alpha.example/doc", "title": "Alpha token guide", "body": "alpha token", "anchor_text": "alpha", "published": "2026-05-18", "quality": 1.0},
                {"url": "https://beta.example/doc", "title": "Beta token guide", "body": "beta token", "anchor_text": "beta", "published": "2026-05-18", "quality": 1.0},
            ]
        }
        stale = [
            {
                "snapshot_hash": "sha256:old",
                "query_id": "q-reused",
                "query_text": "alpha token",
                "shard": "main",
                "limit": 3,
                "results": [
                    {"canonical_url": "https://stale.example/doc", "selected_url": "https://stale.example/doc", "title": "Stale Alpha", "score": 88.0, "published": "2020-01-01", "source_shard": "main", "matched_terms": ["alpha"], "supporting_urls": ["https://stale.example/doc"]}
                ],
            }
        ]
        plan, out, cache, _ = make_case(tmp_path, docs_by_shard=docs, queries=[{"id": "q-reused", "text": "alpha token"}], robots="https://\tallow\n", limit=3, stale_entries=stale)
        first = run_search(plan, out)
        assert results_at(first, 0)[0]["canonical_url"] == docs[shard_id][0]["url"]
        assert first["provenance"]["segments"][0]["cache_status"] == "stale"
        second = run_search(plan, out)
        assert second["provenance"]["segments"][0]["cache_status"] == "hit"
        new_query_text = docs[shard_id][1]["body"]
        write_jsonl(plan.parent / "queries.jsonl", [{"id": "q-reused", "text": new_query_text}])
        third = run_search(plan, out)
        assert results_at(third, 0)[0]["canonical_url"] == docs[shard_id][1]["url"]
        cache_doc = json.loads(cache.read_text(encoding="utf-8"))
        assert cache_doc["entries"][0]["query_text"] == new_query_text
        assert cache_doc["entries"][0]["snapshot_hash"] == third["snapshot_hash"]

    def test_snapshot_hash_tracks_shard_canonical_and_robots_bytes(self, tmp_path):
        """The snapshot digest and cache boundary must move when a shard file changes without a query id change."""
        main_docs = [
            {"url": "https://one.example/doc", "title": "Gamma launch note", "body": "gamma", "anchor_text": "gamma", "published": "2026-05-10", "quality": 1.0},
            {"url": "https://two.example/doc", "title": "Delta launch note", "body": "delta", "anchor_text": "delta", "published": "2026-05-10", "quality": 1.0},
        ]
        docs = {"main": main_docs}
        plan, out, _, snap = make_case(tmp_path, docs_by_shard=docs, queries=[{"id": "q-change", "text": "gamma"}], robots="https://\tallow\n", limit=2)
        first = run_search(plan, out)
        first_expected_url = main_docs[0]["url"]
        second_expected_url = main_docs[1]["url"]
        assert results_at(first, 0)[0]["canonical_url"] == first_expected_url
        main_docs[0]["title"] = "Unrelated note"
        main_docs[0]["body"] = "nothing"
        main_docs[0]["anchor_text"] = "nothing"
        main_docs[1]["title"] = "Gamma launch note"
        main_docs[1]["body"] = "gamma gamma"
        main_docs[1]["anchor_text"] = "gamma"
        write_jsonl(snap / "shards" / "main.jsonl", main_docs)
        second = run_search(plan, out)
        assert second["snapshot_hash"] != first["snapshot_hash"]
        assert results_at(second, 0)[0]["canonical_url"] == second_expected_url
        assert second["provenance"]["segments"][0]["cache_status"] == "stale"

    def test_robots_are_raw_url_authority_before_canonical_merge(self, tmp_path):
        """Disallowed fetched URLs must not win through an allowed canonical URL, and duplicates collapse by canonical URL."""
        docs = {
            "a": [
                {"url": "https://allowed.example/page", "title": "Nimbus relay handbook", "body": "nimbus relay", "anchor_text": "nimbus", "published": "2026-05-10", "quality": 1.0},
                {"url": "https://allowed.example/page?print=1", "title": "Nimbus relay handbook print", "body": "nimbus relay relay", "anchor_text": "nimbus", "published": "2026-05-12", "quality": 2.0},
            ],
            "b": [
                {"url": "https://mirror.bad/page", "title": "Nimbus relay forbidden mirror", "body": "nimbus relay relay relay relay", "anchor_text": "nimbus relay", "published": "2026-05-19", "quality": 20.0},
                {"url": "https://allowed.example/private/secret", "title": "Nimbus relay private draft", "body": "nimbus relay relay", "anchor_text": "nimbus", "published": "2026-05-19", "quality": 15.0},
            ],
        }
        canonical_target = "https://target.example/page"
        allowed_page = docs["a"][0]["url"]
        allowed_print = docs["a"][1]["url"]
        forbidden_mirror = docs["b"][0]["url"]
        forbidden_private = docs["b"][1]["url"]
        canonical = "".join([
            f"{allowed_page}\t{canonical_target}\n",
            f"{allowed_print}\t{canonical_target}\n",
            f"{forbidden_mirror}\t{canonical_target}\n",
            f"{forbidden_private}\t{canonical_target}\n",
        ])
        robots = "https://\tallow\nhttps://mirror.bad/\tdisallow\nhttps://allowed.example/\tallow\nhttps://allowed.example/private/\tdisallow\n"
        plan, out, _, _ = make_case(tmp_path, docs_by_shard=docs, queries=[{"id": "q-nimbus", "text": "nimbus relay"}], canonical=canonical, robots=robots, limit=5)
        report = run_search(plan, out)
        results = results_at(report, 0)
        result_canonicals = [r["canonical_url"] for r in results]
        assert canonical_target in result_canonicals
        assert len(result_canonicals) == len(set(result_canonicals))
        top = results[0]
        assert top["canonical_url"] == canonical_target
        assert top["selected_url"] == allowed_print
        assert top["supporting_urls"] == [allowed_page, allowed_print]
        assert all("mirror.bad" not in url and "/private/" not in url for url in top["supporting_urls"])

    def test_quoted_phrase_boost_and_result_tie_breaks(self, tmp_path):
        """Quoted phrases use the phrase boost, while final ordering still follows score/date/canonical URL."""
        shard_id = "main"
        docs = {
            shard_id: [
                {"url": "https://phrase.example/a", "title": "Reef lantern repair", "body": "field notes", "anchor_text": "repair", "published": "2026-05-11", "quality": 0.5},
                {"url": "https://phrase.example/b", "title": "Lantern reef repair", "body": "reef and lantern repair", "anchor_text": "repair", "published": "2026-05-19", "quality": 6.0},
                {"url": "https://aaa.example/tie", "title": "Orchid index", "body": "orchid", "anchor_text": "", "published": "2026-05-01", "quality": 1.0},
                {"url": "https://bbb.example/tie", "title": "Orchid index", "body": "orchid", "anchor_text": "", "published": "2026-05-01", "quality": 1.0},
            ]
        }
        plan, out, _, _ = make_case(
            tmp_path,
            docs_by_shard=docs,
            queries=[{"id": "q-phrase", "text": "\"reef lantern\" repair"}, {"id": "q-tie", "text": "orchid"}],
            robots="https://\tallow\n",
            limit=5,
        )
        report = run_search(plan, out)
        phrase_results = results_at(report, 0)
        tie_results = results_at(report, 1)
        assert phrase_results[0]["canonical_url"] == docs[shard_id][0]["url"]
        assert phrase_results[0]["score"] > phrase_results[1]["score"]
        assert [r["canonical_url"] for r in tie_results[:2]] == [docs[shard_id][2]["url"], docs[shard_id][3]["url"]]

    def test_report_schema_cache_entries_and_second_replay_hits(self, tmp_path):
        """Structured output, cache entries, and segment provenance must agree across clean and replay runs."""
        docs = {
            "left": [
                {"url": "https://left.example/doc", "title": "Vector search basics", "body": "vector search cache", "anchor_text": "vector", "published": "2026-05-10", "quality": 1.1}
            ],
            "right": [
                {"url": "https://right.example/doc", "title": "Search cache replay", "body": "cache replay vector", "anchor_text": "search", "published": "2026-05-11", "quality": 1.2}
            ],
        }
        plan, out, cache, _ = make_case(tmp_path, docs_by_shard=docs, queries=[{"id": "q-vector", "text": "vector search cache"}], robots="https://\tallow\n", limit=2)
        first = run_search(plan, out)
        second = run_search(plan, out)
        assert first["schema_version"] == "offline-search-run-v1"
        assert second["snapshot_hash"] == first["snapshot_hash"]
        assert results_at(second, 0) == results_at(first, 0)
        assert [r["rank"] for r in results_at(second, 0)] == [1, 2]
        assert all(seg["cache_status"] == "hit" for seg in second["provenance"]["segments"])
        cache_doc = json.loads(cache.read_text(encoding="utf-8"))
        assert cache_doc["schema_version"] == "segment-cache-v1"
        assert len(cache_doc["entries"]) == 2
        for entry in cache_doc["entries"]:
            assert entry["snapshot_hash"] == second["snapshot_hash"]
            assert entry["query_id"] == query_at(second, 0)["id"]
            assert entry["query_text"] == query_at(second, 0)["text"]
            assert entry["limit"] == 2
            assert isinstance(entry["results"], list)
