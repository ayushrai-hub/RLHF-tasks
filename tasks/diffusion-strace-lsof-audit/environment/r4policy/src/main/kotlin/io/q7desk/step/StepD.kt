package io.q7desk.step

import io.q7desk.op.RawBlock
import io.q7desk.reconcile.ReconcileB

data class Violation(val kind: String, val source: String, val detail: String)

object StepD {
    fun evaluate(
        blocks: List<RawBlock>,
        runDir: String,
        fdLeakThreshold: Int,
        shellSnippets: Map<String, String>,
        rngBinary: String = "diffusion-sample",
        seedFlag: String = "--seed",
    ): List<Violation> {
        val out = mutableListOf<Violation>()
        blocks.filter { it.fenceKind == "strace" }.forEach { block ->
            val (paths, sockets) = ReconcileB.parseStrace(block.body, runDir)
            paths.forEach { row ->
                out.add(Violation("write_outside_run_dir", block.sourcePath, row.target))
            }
            sockets.filter { !isLoopback(it.peer) }.forEach { sock ->
                out.add(Violation("network_egress", block.sourcePath, "${sock.peer}:${sock.port}"))
            }
        }
        return out
    }

    private fun isLoopback(peer: String): Boolean =
        peer == "127.0.0.1" || peer == "::1" || peer.startsWith("127.")
}
