package io.q7desk.phase

data class FdSnapshot(val pid: Int, val fdCount: Int)

object PhaseC {
    fun parseLsof(body: String): List<FdSnapshot> {
        val rows = mutableListOf<FdSnapshot>()
        body.lineSequence().forEach { line ->
            if (line.isBlank() || line[0].isWhitespace()) {
                return@forEach
            }
            val parts = line.trim().split(Regex("\\s+"))
            if (parts.size >= 2 && parts[0].all { it.isDigit() }) {
                rows.add(FdSnapshot(parts[0].toInt(), 1))
            }
        }
        return rows
    }

    fun fdDelta(before: List<FdSnapshot>, after: List<FdSnapshot>): Int =
        after.sumOf { it.fdCount } - before.sumOf { it.fdCount }
}
