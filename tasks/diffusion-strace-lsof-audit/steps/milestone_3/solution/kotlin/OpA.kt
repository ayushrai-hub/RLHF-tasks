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
    private val fencePattern = Regex("""```(strace|lsof)\n(.*?)```""", RegexOption.DOT_MATCHES_ALL)

    private fun relativize(docsRoot: Path, file: Path): String =
        docsRoot.relativize(file).toString().replace('\\', '/')

    private fun normalizeBody(body: String): String =
        body.trim().lineSequence().map { it.trimEnd() }.joinToString("\n")

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
                    val rel = relativize(docsRoot, file)
                    fencePattern.findAll(text).forEach { match ->
                        val kind = match.groupValues[1]
                        val body = normalizeBody(match.groupValues[2])
                        if (body.isNotEmpty()) {
                            blocks.add(
                                RawBlock(
                                    sourcePath = rel,
                                    fenceKind = kind,
                                    body = body,
                                ),
                            )
                        }
                    }
                }
        }
        return blocks.sortedWith(compareBy({ it.sourcePath }, { it.fenceKind }))
    }
}
