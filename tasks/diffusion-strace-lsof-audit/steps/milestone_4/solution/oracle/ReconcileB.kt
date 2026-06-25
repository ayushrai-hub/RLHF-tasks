package io.q7desk.reconcile

data class PathRow(val kind: String, val target: String)
data class SocketRow(val peer: String, val port: Int)

object ReconcileB {
    private val openPattern = Regex("""openat\([^,]+,\s*"([^"]+)"""")
    private val connectPattern = Regex(
        """sin_port=htons\((\d+)\).*sin_addr=inet_addr\("([^"]+)"\)""",
    )

    fun parseStrace(body: String, runDir: String): Pair<List<PathRow>, List<SocketRow>> {
        val paths = mutableListOf<PathRow>()
        val sockets = mutableListOf<SocketRow>()
        val normalizedRun = runDir.trimEnd('/')
        body.lineSequence().forEach { line ->
            openPattern.find(line)?.let { match ->
                val target = match.groupValues[1]
                if (!target.startsWith(normalizedRun)) {
                    val kind = if (line.contains("O_WRONLY") || line.contains("O_RDWR")) "write" else "open"
                    paths.add(PathRow(kind, target))
                }
            }
            connectPattern.find(line)?.let { match ->
                val port = match.groupValues[1].toInt()
                val peer = match.groupValues[2]
                sockets.add(SocketRow(peer, port))
            }
        }
        return paths to sockets
    }
}
