package com.terminus.pubgate

import com.google.gson.GsonBuilder
import java.io.File
import java.sql.DriverManager

data class Column(val name: String, val type: String, val nullable: Boolean, val primaryKey: Boolean)
data class TableSnapshot(val schema: String, val name: String, val columns: List<Column>, val replicaIdentity: String)

fun main(args: Array<String>) {
    val command = args.firstOrNull() ?: error("command required")
    val opts = parseOptions(args.drop(1))
    when (command) {
        "parse" -> parse(opts)
        "validate" -> {
            println("validate is not wired yet")
            kotlin.system.exitProcess(2)
        }
        "plan" -> {
            println("plan is not wired yet")
            kotlin.system.exitProcess(2)
        }
        else -> error("unknown command: $command")
    }
}

fun parseOptions(args: List<String>): Map<String, String> {
    val out = linkedMapOf<String, String>()
    var i = 0
    while (i < args.size) {
        val key = args[i]
        if (!key.startsWith("--") || i + 1 >= args.size) error("bad option near $key")
        out[key.removePrefix("--")] = args[i + 1]
        i += 2
    }
    return out
}

fun parse(opts: Map<String, String>) {
    val schemaPath = opts["schema"] ?: error("--schema required")
    val dbPath = opts["db"] ?: error("--db required")
    val outPath = opts["out"] ?: error("--out required")
    val tables = parseTables(File(schemaPath).readText())
    writeSqlite(dbPath, tables)
    val payload = linkedMapOf<String, Any>(
        "tables" to tables,
        "publications" to emptyList<Any>(),
        "subscriptions" to emptyList<Any>()
    )
    writeJson(outPath, payload)
}

fun parseTables(sql: String): List<TableSnapshot> {
    val create = Regex("""(?is)CREATE\s+TABLE\s+([a-zA-Z_][\w]*)\.([a-zA-Z_][\w]*)\s*\((.*?)\);""")
    return create.findAll(sql).map { m ->
        val cols = m.groupValues[3].split(",").mapNotNull { raw ->
            val line = raw.trim()
            if (line.isBlank() || line.startsWith("constraint", true)) null else {
                val parts = line.split(Regex("""\s+"""))
                Column(
                    parts[0].trim('"'),
                    parts.drop(1).takeWhile { !it.equals("primary", true) && !it.equals("not", true) }.joinToString(" ").ifBlank { "text" },
                    !line.contains("not null", true),
                    line.contains("primary key", true)
                )
            }
        }.sortedBy { it.name }
        TableSnapshot(m.groupValues[1], m.groupValues[2], cols, "default")
    }.sortedWith(compareBy<TableSnapshot> { it.schema }.thenBy { it.name }).toList()
}

fun writeSqlite(path: String, tables: List<TableSnapshot>) {
    File(path).parentFile?.mkdirs()
    DriverManager.getConnection("jdbc:sqlite:$path").useAuto { conn ->
        conn.createStatement().useAuto { st ->
            st.executeUpdate("DROP TABLE IF EXISTS columns")
            st.executeUpdate("DROP TABLE IF EXISTS tables")
            st.executeUpdate("CREATE TABLE tables(schema_name TEXT, table_name TEXT, replica_identity TEXT)")
            st.executeUpdate("CREATE TABLE columns(schema_name TEXT, table_name TEXT, column_name TEXT, data_type TEXT, nullable INTEGER, primary_key INTEGER)")
        }
        conn.prepareStatement("INSERT INTO tables VALUES (?, ?, ?)").useAuto { ps ->
            for (t in tables) {
                ps.setString(1, t.schema); ps.setString(2, t.name); ps.setString(3, t.replicaIdentity); ps.executeUpdate()
            }
        }
        conn.prepareStatement("INSERT INTO columns VALUES (?, ?, ?, ?, ?, ?)").useAuto { ps ->
            for (t in tables) for (c in t.columns) {
                ps.setString(1, t.schema); ps.setString(2, t.name); ps.setString(3, c.name)
                ps.setString(4, c.type); ps.setInt(5, if (c.nullable) 1 else 0); ps.setInt(6, if (c.primaryKey) 1 else 0)
                ps.executeUpdate()
            }
        }
    }
}

fun writeJson(path: String, value: Any) {
    File(path).parentFile?.mkdirs()
    File(path).writeText(GsonBuilder().setPrettyPrinting().create().toJson(value) + "\n")
}

inline fun <T : AutoCloseable, R> T.useAuto(block: (T) -> R): R {
    try {
        return block(this)
    } finally {
        close()
    }
}
