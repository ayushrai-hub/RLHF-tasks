#!/bin/bash
set -euo pipefail

cat > /app/src/main/kotlin/com/terminus/pubgate/Main.kt <<'KOTLIN'
package com.terminus.pubgate

import com.google.gson.GsonBuilder
import com.google.gson.JsonParser
import java.io.File
import java.sql.DriverManager

data class Column(val name: String, val type: String, val nullable: Boolean, val primaryKey: Boolean)
data class TableSnapshot(val schema: String, val name: String, val columns: List<Column>, val replicaIdentity: String)
data class TableRef(val schema: String, val name: String, val columns: List<String>)
data class Publication(val name: String, val tables: List<TableRef>)
data class Subscription(val name: String, val publication: String, val targetTables: List<TableRef>)

fun main(args: Array<String>) {
    val command = args.firstOrNull() ?: error("command required")
    val opts = parseOptions(args.drop(1))
    when (command) {
        "parse" -> parse(opts)
        "validate" -> { System.err.println("validate is not implemented in this stage"); kotlin.system.exitProcess(2) }
        "plan" -> { System.err.println("plan is not implemented in this stage"); kotlin.system.exitProcess(2) }
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
    val tables = parseTables(File(opts["schema"] ?: error("--schema required")).readText())
    val publications = parsePublications(File(opts["publications"] ?: error("--publications required")).readText())
    val subscriptions = parseSubscriptions(File(opts["subscriptions"] ?: error("--subscriptions required")).readText())
    writeSqlite(opts["db"] ?: error("--db required"), tables, publications, subscriptions)
    writeJson(opts["out"] ?: error("--out required"), linkedMapOf(
        "tables" to tables,
        "publications" to publications,
        "subscriptions" to subscriptions
    ))
}

fun parseTables(sql: String): List<TableSnapshot> {
    val full = Regex("""(?is)ALTER\s+TABLE\s+([a-zA-Z_][\w]*)\.([a-zA-Z_][\w]*)\s+REPLICA\s+IDENTITY\s+FULL""")
        .findAll(sql).map { it.groupValues[1] + "." + it.groupValues[2] }.toSet()
    val create = Regex("""(?is)CREATE\s+TABLE\s+([a-zA-Z_][\w]*)\.([a-zA-Z_][\w]*)\s*\((.*?)\);""")
    return create.findAll(sql).map { m ->
        val schema = m.groupValues[1]
        val name = m.groupValues[2]
        val bodyParts = splitTopLevel(m.groupValues[3])
        val tablePk = bodyParts.map { it.trim() }.filter { it.startsWith("primary key", true) }
            .flatMap { pk ->
                Regex("""(?is)PRIMARY\s+KEY\s*\(([^)]*)\)""").find(pk)?.groupValues?.get(1)
                    ?.split(",")?.map { it.trim().trim('"') } ?: emptyList()
            }.toSet()
        val columns = bodyParts.mapNotNull { raw ->
            val line = raw.trim()
            if (line.isBlank() || line.startsWith("constraint", true) || line.startsWith("primary key", true)) null else {
                val parts = line.split(Regex("""\s+"""))
                val type = parts.drop(1).takeWhile {
                    val low = it.toLowerCase()
                    low != "primary" && low != "not" && low != "references" && low != "constraint"
                }.joinToString(" ").ifBlank { "text" }
                val columnName = parts[0].trim('"')
                val isPk = line.contains("primary key", true) || tablePk.contains(columnName)
                Column(columnName, type, !isPk && !line.contains("not null", true), isPk)
            }
        }.sortedBy { it.name }
        TableSnapshot(schema, name, columns, if (full.contains("$schema.$name")) "full" else "default")
    }.sortedWith(compareBy<TableSnapshot> { it.schema }.thenBy { it.name }).toList()
}

fun parsePublications(sql: String): List<Publication> {
    val pubs = linkedMapOf<String, MutableList<TableRef>>()
    for (stmt in sql.split(";").map { it.trim() }.filter { it.isNotBlank() }) {
        val create = Regex("""(?is)^CREATE\s+PUBLICATION\s+([a-zA-Z_][\w]*)(?:\s+FOR\s+TABLE\s+(.+))?$""").find(stmt)
        val alter = Regex("""(?is)^ALTER\s+PUBLICATION\s+([a-zA-Z_][\w]*)\s+ADD\s+TABLE\s+(.+)$""").find(stmt)
        if (create != null) {
            val name = create.groupValues[1]
            pubs.putIfAbsent(name, mutableListOf())
            val refs = create.groupValues.getOrElse(2) { "" }.trim()
            if (refs.isNotBlank()) pubs[name]!!.addAll(parseRefs(refs))
        } else if (alter != null) {
            val name = alter.groupValues[1]
            pubs.putIfAbsent(name, mutableListOf())
            pubs[name]!!.addAll(parseRefs(alter.groupValues[2]))
        }
    }
    return pubs.map { Publication(it.key, it.value.sortedWith(compareBy<TableRef> { r -> r.schema }.thenBy { r -> r.name })) }.sortedBy { it.name }
}

fun parseRefs(text: String): List<TableRef> = splitTopLevel(text).map { raw ->
    val m = Regex("""(?is)^\s*([a-zA-Z_][\w]*)\.([a-zA-Z_][\w]*)(?:\s*\(([^)]*)\))?\s*$""").find(raw) ?: error("bad table ref: $raw")
    val cols = m.groupValues.getOrElse(3) { "" }.split(",").map { it.trim() }.filter { it.isNotBlank() }
    TableRef(m.groupValues[1], m.groupValues[2], cols)
}

fun parseSubscriptions(pathText: String): List<Subscription> {
    val root = JsonParser().parse(pathText).asJsonObject
    return root.getAsJsonArray("subscriptions").map { item ->
        val obj = item.asJsonObject
        val refs = obj.getAsJsonArray("tables").map { t ->
            val to = t.asJsonObject
            TableRef(to.get("schema").asString, to.get("name").asString, to.getAsJsonArray("columns").map { it.asString })
        }.sortedWith(compareBy<TableRef> { it.schema }.thenBy { it.name })
        Subscription(obj.get("name").asString, obj.get("publication").asString, refs)
    }.sortedBy { it.name }
}

fun splitTopLevel(text: String): List<String> {
    val out = mutableListOf<String>()
    val buf = StringBuilder()
    var depth = 0
    for (ch in text) {
        when (ch) {
            '(' -> { depth++; buf.append(ch) }
            ')' -> { depth--; buf.append(ch) }
            ',' -> if (depth == 0) { out.add(buf.toString()); buf.setLength(0) } else buf.append(ch)
            else -> buf.append(ch)
        }
    }
    if (buf.isNotBlank()) out.add(buf.toString())
    return out
}

fun writeSqlite(path: String, tables: List<TableSnapshot>, pubs: List<Publication>, subs: List<Subscription>) {
    File(path).parentFile?.mkdirs()
    DriverManager.getConnection("jdbc:sqlite:$path").useAuto { conn ->
        conn.createStatement().useAuto { st ->
            st.executeUpdate("DROP TABLE IF EXISTS subscription_tables")
            st.executeUpdate("DROP TABLE IF EXISTS subscriptions")
            st.executeUpdate("DROP TABLE IF EXISTS publication_tables")
            st.executeUpdate("DROP TABLE IF EXISTS publications")
            st.executeUpdate("DROP TABLE IF EXISTS columns")
            st.executeUpdate("DROP TABLE IF EXISTS tables")
            st.executeUpdate("CREATE TABLE tables(schema_name TEXT, table_name TEXT, replica_identity TEXT)")
            st.executeUpdate("CREATE TABLE columns(schema_name TEXT, table_name TEXT, column_name TEXT, data_type TEXT, nullable INTEGER, primary_key INTEGER)")
            st.executeUpdate("CREATE TABLE publications(publication_name TEXT)")
            st.executeUpdate("CREATE TABLE publication_tables(publication_name TEXT, schema_name TEXT, table_name TEXT, columns_json TEXT)")
            st.executeUpdate("CREATE TABLE subscriptions(subscription_name TEXT, publication_name TEXT)")
            st.executeUpdate("CREATE TABLE subscription_tables(subscription_name TEXT, schema_name TEXT, table_name TEXT, columns_json TEXT)")
        }
        conn.prepareStatement("INSERT INTO tables VALUES (?, ?, ?)").useAuto { ps -> for (t in tables) { ps.setString(1,t.schema); ps.setString(2,t.name); ps.setString(3,t.replicaIdentity); ps.executeUpdate() } }
        conn.prepareStatement("INSERT INTO columns VALUES (?, ?, ?, ?, ?, ?)").useAuto { ps -> for (t in tables) for (c in t.columns) { ps.setString(1,t.schema); ps.setString(2,t.name); ps.setString(3,c.name); ps.setString(4,c.type); ps.setInt(5, if(c.nullable)1 else 0); ps.setInt(6, if(c.primaryKey)1 else 0); ps.executeUpdate() } }
        conn.prepareStatement("INSERT INTO publications VALUES (?)").useAuto { ps -> for (p in pubs) { ps.setString(1,p.name); ps.executeUpdate() } }
        conn.prepareStatement("INSERT INTO publication_tables VALUES (?, ?, ?, ?)").useAuto { ps -> for (p in pubs) for (t in p.tables) { ps.setString(1,p.name); ps.setString(2,t.schema); ps.setString(3,t.name); ps.setString(4,jsonCompact(t.columns)); ps.executeUpdate() } }
        conn.prepareStatement("INSERT INTO subscriptions VALUES (?, ?)").useAuto { ps -> for (s in subs) { ps.setString(1,s.name); ps.setString(2,s.publication); ps.executeUpdate() } }
        conn.prepareStatement("INSERT INTO subscription_tables VALUES (?, ?, ?, ?)").useAuto { ps -> for (s in subs) for (t in s.targetTables) { ps.setString(1,s.name); ps.setString(2,t.schema); ps.setString(3,t.name); ps.setString(4,jsonCompact(t.columns)); ps.executeUpdate() } }
    }
}

fun jsonCompact(value: Any): String = GsonBuilder().create().toJson(value)
fun writeJson(path: String, value: Any) { File(path).parentFile?.mkdirs(); File(path).writeText(GsonBuilder().setPrettyPrinting().create().toJson(value) + "\n") }
inline fun <T : AutoCloseable, R> T.useAuto(block: (T) -> R): R { try { return block(this) } finally { close() } }
KOTLIN

/app/build.sh
java -cp /app/build/pubgate.jar:/usr/share/java/gson.jar:/usr/share/java/sqlite-jdbc.jar:/usr/share/java/kotlin-stdlib.jar:/usr/share/java/kotlin-stdlib-jdk7.jar:/usr/share/java/kotlin-stdlib-jdk8.jar com.terminus.pubgate.MainKt parse --schema /app/input/publisher_schema.sql --publications /app/input/publications.sql --subscriptions /app/input/subscriptions.json --db /tmp/pubgate-smoke.db --out /tmp/pubgate-smoke.json
