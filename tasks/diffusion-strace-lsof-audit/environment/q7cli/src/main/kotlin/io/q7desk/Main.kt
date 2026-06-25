package io.q7desk

import io.q7desk.op.OpA
import io.q7desk.op.RawBlock
import io.q7desk.step.StepD
import io.q7desk.step.Violation
import java.nio.file.Files
import java.nio.file.Path
import java.security.MessageDigest
import kotlin.io.path.readText

fun main(args: Array<String>) {
    if (args.isEmpty()) {
        System.err.println("usage: index <out> | audit <index> <out> | clean <audit> <out> | verify <out>")
        kotlin.system.exitProcess(2)
    }
    when (args[0]) {
        "index" -> runIndex(Path.of(args[1]))
        "audit" -> runAudit(Path.of(args[1]), Path.of(args[2]))
        "clean" -> runClean(Path.of(args[1]), Path.of(args[2]))
        "verify" -> runVerify(Path.of(args[1]))
        else -> {
            System.err.println("unknown subcommand")
            kotlin.system.exitProcess(2)
        }
    }
}

private fun runIndex(out: Path) {
    val docs = Path.of("/app/docs/q3_bundles")
    val blocks = OpA.harvest(docs)
    val kinds = blocks.map { it.fenceKind }.distinct().sorted()
    val payload = buildString {
        append("{\n")
        append("  \"schema_tag\": \"tb3-kdiff-trace-01\",\n")
        append("  \"sources_scanned\": ").append(countSources(docs)).append(",\n")
        append("  \"trace_blocks\": ").append(blocks.size).append(",\n")
        append("  \"fence_kinds\": ").append(jsonStringList(kinds)).append(",\n")
        append("  \"blocks\": [\n")
        blocks.forEachIndexed { idx, block ->
            append("    {\"source_path\":\"").append(escape(block.sourcePath)).append("\",")
            append("\"fence_kind\":\"").append(block.fenceKind).append("\",")
            append("\"line_count\":").append(block.body.lines().size).append("}")
            if (idx < blocks.size - 1) append(",")
            append("\n")
        }
        append("  ]\n")
        append("}\n")
    }
    Files.writeString(out, payload)
}

private fun runAudit(indexPath: Path, out: Path) {
    val docs = Path.of("/app/docs/q3_bundles")
    val policy = loadPolicy(Path.of("/app/policy/workflow_policy.toml"))
    val blocks = OpA.harvest(docs)
    val snippets = loadShellSnippets(docs)
    val violations = StepD.evaluate(
        blocks,
        policy.runDir,
        policy.fdLeakThreshold,
        snippets,
        policy.rngBinary,
        policy.seedFlag,
    )
    val socketRows = mutableListOf<String>()
    blocks.filter { it.fenceKind == "strace" }.forEach { block ->
        val (_, sockets) = io.q7desk.reconcile.ReconcileB.parseStrace(block.body, policy.runDir)
        sockets.filter { !isLoopback(it.peer) }.forEach { sock -> socketRows.add(formatPeer(sock)) }
    }
    val payload = buildString {
        append("{\n")
        append("  \"schema_tag\": \"tb3-kdiff-trace-02\",\n")
        append("  \"violation_count\": ").append(violations.size).append(",\n")
        append("  \"violation_kinds\": ").append(jsonStringList(violations.map { it.kind }.distinct().sorted())).append(",\n")
        append("  \"run_dir\": \"").append(escape(policy.runDir)).append("\",\n")
        append("  \"socket_rows\": ").append(jsonStringList(socketRows.sorted())).append(",\n")
        append("  \"violations\": [\n")
        violations.forEachIndexed { idx, v ->
            append("    {\"kind\":\"").append(v.kind).append("\",")
            append("\"source\":\"").append(escape(v.source)).append("\",")
            append("\"detail\":\"").append(escape(v.detail)).append("\"}")
            if (idx < violations.size - 1) append(",")
            append("\n")
        }
        append("  ]\n")
        append("}\n")
    }
    Files.writeString(out, payload)
}

private fun runClean(auditPath: Path, out: Path) {
    val docs = Path.of("/app/docs/q3_bundles")
    val policy = loadPolicy(Path.of("/app/policy/workflow_policy.toml"))
    val blocks = OpA.harvest(docs)
    val snippets = loadShellSnippets(docs)
    val violations = StepD.evaluate(
        blocks,
        policy.runDir,
        policy.fdLeakThreshold,
        snippets,
        policy.rngBinary,
        policy.seedFlag,
    )
    val digest = runbookDigest(docs)
    val payload = buildString {
        append("{\n")
        append("  \"schema_tag\": \"tb3-kdiff-trace-03\",\n")
        append("  \"open_violations\": ").append(violations.size).append(",\n")
        append("  \"policy_pass_count\": ").append(policyPassCount(violations)).append(",\n")
        append("  \"runbook_sha256\": \"").append(digest).append("\"\n")
        append("}\n")
    }
    Files.writeString(out, payload)
}

private fun runVerify(out: Path) {
    val manifestPath = Path.of("/app/data/scenario_manifest.json")
    val manifestText = manifestPath.readText()
    val manifestVersion = fieldValue(manifestText, "manifest_version") ?: ""
    val expectedSources = fieldValue(manifestText, "expected_sources")?.toIntOrNull() ?: 0
    val expectedBlocks = fieldValue(manifestText, "expected_trace_blocks")?.toIntOrNull() ?: 0
    val docs = Path.of("/app/docs/q3_bundles")
    val blocks = OpA.harvest(docs)
    val policy = loadPolicy(Path.of("/app/policy/workflow_policy.toml"))
    val snippets = loadShellSnippets(docs)
    val violations = StepD.evaluate(
        blocks,
        policy.runDir,
        policy.fdLeakThreshold,
        snippets,
        policy.rngBinary,
        policy.seedFlag,
    )
    val relayPath = docs.resolve("relay_lane.md")
    val relayText = if (Files.isRegularFile(relayPath)) relayPath.readText() else ""
    val relayStrace = fenceBody(relayText, "strace") ?: ""
    val relayLsof = fenceBody(relayText, "lsof") ?: ""
    val relayOffline = relayText.isNotEmpty() &&
        "connect(" !in relayStrace &&
        "/etc/diffusion" !in relayStrace &&
        "/etc/diffusion" !in relayLsof
    val payload = buildString {
        append("{\n")
        append("  \"schema_tag\": \"tb3-kdiff-trace-04\",\n")
        append("  \"manifest_version\": \"").append(escape(manifestVersion)).append("\",\n")
        append("  \"bundles_scanned\": ").append(countSources(docs)).append(",\n")
        append("  \"trace_blocks_harvested\": ").append(blocks.size).append(",\n")
        append("  \"audit_clean\": ").append(violations.isEmpty()).append(",\n")
        append("  \"relay_lane_offline\": ").append(relayOffline).append(",\n")
        append("  \"manifest_sources_match\": ").append(countSources(docs) == expectedSources).append(",\n")
        append("  \"manifest_blocks_match\": ").append(blocks.size == expectedBlocks).append("\n")
        append("}\n")
    }
    Files.writeString(out, payload)
}

private data class Policy(
    val runDir: String,
    val fdLeakThreshold: Int,
    val rngBinary: String,
    val seedFlag: String,
)

private fun loadPolicy(path: Path): Policy {
    val text = path.readText()
    val runDir = regexValue(text, "run_dir") ?: "/var/lib/diffusion-runs/current"
    val threshold = regexValue(text, "fd_leak_threshold")?.toIntOrNull() ?: 4
    val rngBinary = regexValue(text, "rng_binary") ?: "diffusion-sample"
    val seedFlag = regexValue(text, "required_seed_flag") ?: "--seed"
    return Policy(runDir, threshold, rngBinary, seedFlag)
}

private fun regexValue(text: String, key: String): String? {
    val pattern = Regex("""$key\s*=\s*"([^"]+)"""")
    return pattern.find(text)?.groupValues?.get(1)
}

private fun fieldValue(text: String, key: String): String? {
    regexValue(text, key)?.let { return it }
    Regex(""""$key"\s*:\s*"([^"]+)"""").find(text)?.groupValues?.get(1)?.let { return it }
    Regex(""""$key"\s*:\s*(\d+)""").find(text)?.groupValues?.get(1)?.let { return it }
    return null
}

private fun countSources(docs: Path): Int {
    if (!Files.isDirectory(docs)) return 0
    return Files.walk(docs).use { stream ->
        stream.filter { Files.isRegularFile(it) && it.fileName.toString().endsWith(".md") }.count().toInt()
    }
}

private fun loadShellSnippets(docs: Path): Map<String, String> {
    val map = linkedMapOf<String, String>()
    if (!Files.isDirectory(docs)) return map
    Files.walk(docs).use { stream ->
        stream.filter { Files.isRegularFile(it) && it.fileName.toString().endsWith(".md") }
            .sorted()
            .forEach { file ->
                val rel = docs.relativize(file).toString().replace('\\', '/')
                val text = file.readText()
                val marker = "<!-- shell-invoke -->"
                val start = text.indexOf(marker)
                if (start >= 0) {
                    val lineStart = text.indexOf('\n', start) + 1
                    val lineEnd = text.indexOf('\n', lineStart)
                    val snippet = if (lineEnd > lineStart) text.substring(lineStart, lineEnd).trim() else ""
                    map[rel] = snippet
                }
            }
    }
    return map
}

private fun runbookDigest(docs: Path): String {
    val md = MessageDigest.getInstance("SHA-256")
    if (!Files.isDirectory(docs)) return md.digest().joinToString("") { "%02x".format(it) }
    Files.walk(docs).use { stream ->
        stream.filter { Files.isRegularFile(it) && it.fileName.toString().endsWith(".md") }
            .sorted()
            .forEach { file ->
                md.update(file.readText().toByteArray())
            }
    }
    return md.digest().joinToString("") { "%02x".format(it) }
}

private fun policyPassCount(violations: List<Violation>): Int {
    val kinds = setOf("rng_unseeded", "write_outside_run_dir", "descriptor_leak", "network_egress")
    val failing = violations.map { it.kind }.toSet()
    return kinds.count { it !in failing }
}

private fun jsonStringList(values: List<String>): String =
    values.joinToString(prefix = "[", postfix = "]") { "\"${escape(it)}\"" }

private fun escape(value: String): String =
    value.replace("\\", "\\\\").replace("\"", "\\\"")

private fun fenceBody(text: String, label: String): String? {
    val marker = "```$label"
    val start = text.indexOf(marker)
    if (start < 0) {
        return null
    }
    val bodyStart = text.indexOf('\n', start) + 1
    val end = text.indexOf("```", bodyStart)
    if (end <= bodyStart) {
        return null
    }
    return text.substring(bodyStart, end)
}

private fun isLoopback(peer: String): Boolean =
    peer == "127.0.0.1" || peer == "::1" || peer.startsWith("127.") || peer.equals("0:0:0:0:0:0:0:1", ignoreCase = true)

private fun formatPeer(sock: io.q7desk.reconcile.SocketRow): String {
    val host = if (sock.peer.contains(":")) "[${sock.peer}]" else sock.peer
    return "$host:${sock.port}"
}
