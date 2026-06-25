package io.q7desk.step

import io.q7desk.op.RawBlock
import io.q7desk.phase.PhaseC
import io.q7desk.reconcile.ReconcileB

data class Violation(val kind: String, val source: String, val detail: String)

object StepD {
    fun evaluate(
        blocks: List<RawBlock>,
        runDir: String,
        fdLeakThreshold: Int,
        shellSnippets: Map<String, String>,
        rngBinary: String,
        seedFlag: String,
    ): List<Violation> {
        val out = linkedSetOf<Violation>()
        blocks.filter { it.fenceKind == "strace" }.forEach { block ->
            val (paths, sockets) = ReconcileB.parseStrace(block.body, runDir)
            paths.forEach { row ->
                out.add(Violation("write_outside_run_dir", block.sourcePath, row.target))
            }
            sockets.filter { !isLoopback(it.peer) }.forEach { sock ->
                out.add(Violation("network_egress", block.sourcePath, "${sock.peer}:${sock.port}"))
            }
        }
        blocks.filter { it.fenceKind == "lsof" }.forEach { block ->
            PhaseC.pathsOutsideRun(block.body, runDir).forEach { path ->
                out.add(Violation("write_outside_run_dir", block.sourcePath, path))
            }
        }
        val bySource = blocks.groupBy { it.sourcePath }
        bySource.forEach { (source, sourceBlocks) ->
            val lsofBodies = sourceBlocks.filter { it.fenceKind == "lsof" }.map { it.body }
            if (lsofBodies.size >= 2) {
                val delta = PhaseC.fdDelta(
                    PhaseC.parseLsof(lsofBodies.first()),
                    PhaseC.parseLsof(lsofBodies.last()),
                )
                if (delta > fdLeakThreshold) {
                    out.add(Violation("descriptor_leak", source, "fd_delta=$delta"))
                }
            }
        }
        shellSnippets.forEach { (source, snippet) ->
            if (snippet.contains(rngBinary) && !snippet.contains(seedFlag)) {
                out.add(Violation("rng_unseeded", source, snippet))
            }
            if (snippet.contains("curl") || snippet.contains("https://")) {
                out.add(Violation("network_egress", source, "shell:$snippet"))
            }
        }
        return out.sortedWith(compareBy({ it.kind }, { it.source }, { it.detail }))
    }

    private fun isLoopback(peer: String): Boolean =
        peer == "127.0.0.1" || peer == "::1" || peer.startsWith("127.")
}
