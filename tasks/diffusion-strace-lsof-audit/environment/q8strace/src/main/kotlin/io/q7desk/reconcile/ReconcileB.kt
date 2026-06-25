package io.q7desk.reconcile

data class PathRow(val kind: String, val target: String)
data class SocketRow(val peer: String, val port: Int)

object ReconcileB {
    fun parseStrace(body: String, runDir: String): Pair<List<PathRow>, List<SocketRow>> {
        val paths = mutableListOf<PathRow>()
        body.lineSequence().forEach { line ->
            if (line.contains("openat(")) {
                paths.add(PathRow("open", "unknown"))
            }
        }
        return paths to emptyList()
    }
}
