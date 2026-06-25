package io.q7desk.op

import java.nio.file.Files
import java.nio.file.Path
import kotlin.io.path.name
import kotlin.io.path.readText

data class RawBlock(
    val sourcePath: String,
    val fenceKind: String,
    val body: String,
)

object OpA {
    private fun stripNoise(line: String): String = line.trim()

    private fun firstFence(text: String, label: String): String? {
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

    fun harvest(docsRoot: Path): List<RawBlock> {
        val blocks = mutableListOf<RawBlock>()
        if (!Files.isDirectory(docsRoot)) {
            return blocks
        }
        Files.walk(docsRoot).use { stream ->
            stream.filter { Files.isRegularFile(it) && it.name.endsWith(".md") }
                .sorted()
                .forEach { file ->
                    val text = file.readText()
                    val body = firstFence(text, "strace")
                    if (body != null) {
                        blocks.add(
                            RawBlock(
                                sourcePath = "",
                                fenceKind = "strace",
                                body = body.lineSequence().map(::stripNoise).joinToString("\n").trim(),
                            ),
                        )
                    }
                }
        }
        return blocks
    }
}
