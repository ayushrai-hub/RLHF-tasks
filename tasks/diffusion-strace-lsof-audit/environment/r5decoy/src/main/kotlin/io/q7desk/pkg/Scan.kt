package io.q7desk.pkg

import java.nio.file.Files
import java.nio.file.Path

object Scan {
    fun headingCount(root: Path): Int {
        if (!Files.isDirectory(root)) {
            return 0
        }
        var count = 0
        Files.walk(root).use { stream ->
            stream.filter { Files.isRegularFile(it) && it.toString().endsWith(".md") }
                .forEach { file ->
                    file.toFile().readText().lineSequence().forEach { line ->
                        if (line.startsWith("#")) {
                            count++
                        }
                    }
                }
        }
        return count
    }
}
