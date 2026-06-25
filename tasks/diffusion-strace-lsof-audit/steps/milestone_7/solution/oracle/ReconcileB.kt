package io.q7desk.reconcile

data class PathRow(val kind: String, val target: String)
data class SocketRow(val peer: String, val port: Int)

object ReconcileB {
    private val openPattern = Regex("""openat\([^,]+,\s*"([^"]+)"""")
    private val htonsPattern = Regex("""htons\(([^)]+)\)""")
    private val inetAddrPattern = Regex("""inet_addr\("([^"]+)"\)""")
    private val inet6Pattern = Regex("""inet_pton\(AF_INET6,\s*"([^"]+)"\)""")

    private fun parsePort(raw: String): Int {
        val token = raw.trim()
        return if (token.startsWith("0x", ignoreCase = true)) {
            token.substring(2).toInt(16)
        } else {
            token.toInt()
        }
    }

    private fun parseConnect(line: String): SocketRow? {
        if (!line.contains("connect(")) {
            return null
        }
        val port = htonsPattern.find(line)?.groupValues?.get(1)?.let(::parsePort) ?: return null
        inet6Pattern.find(line)?.let { match ->
            return SocketRow(match.groupValues[1], port)
        }
        inetAddrPattern.find(line)?.let { match ->
            return SocketRow(match.groupValues[1], port)
        }
        return null
    }

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
            parseConnect(line)?.let { sockets.add(it) }
        }
        return paths to sockets
    }
}
