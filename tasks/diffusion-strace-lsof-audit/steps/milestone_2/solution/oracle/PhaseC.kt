package io.q7desk.phase

data class FdSnapshot(val pid: Int, val fdCount: Int)

object PhaseC {
    fun parseLsof(body: String): List<FdSnapshot> {
        var currentPid = -1
        var count = 0
        body.lineSequence().forEach { raw ->
            val line = raw.trim()
            if (line.isBlank()) {
                return@forEach
            }
            val parts = line.split(Regex("\\s+"))
            if (parts.isNotEmpty() && parts[0].all { it.isDigit() }) {
                currentPid = parts[0].toInt()
                count += 1
            } else if (currentPid > 0) {
                count += 1
            }
        }
        return if (currentPid > 0) listOf(FdSnapshot(currentPid, count)) else emptyList()
    }

    fun fdDelta(before: List<FdSnapshot>, after: List<FdSnapshot>): Int {
        val beforeTotal = before.sumOf { it.fdCount }
        val afterTotal = after.sumOf { it.fdCount }
        return afterTotal - beforeTotal
    }

    fun pathsOutsideRun(body: String, runDir: String): List<String> {
        val normalizedRun = runDir.trimEnd('/')
        val paths = mutableListOf<String>()
        body.lineSequence().forEach { line ->
            line.split(Regex("\\s+")).forEach { token ->
                if (token.startsWith("/") && !token.startsWith(normalizedRun)) {
                    paths.add(token)
                }
            }
        }
        return paths.distinct().sorted()
    }
}
