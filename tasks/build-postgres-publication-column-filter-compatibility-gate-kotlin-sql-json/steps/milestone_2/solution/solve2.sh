#!/bin/bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path

path = Path("/app/src/main/kotlin/com/terminus/pubgate/Main.kt")
text = path.read_text()
text = text.replace('"validate" -> { System.err.println("validate is not implemented in this stage"); kotlin.system.exitProcess(2) }', '"validate" -> validate(opts)')
if "fun validate(opts: Map<String, String>)" not in text:
    text += r'''

fun validate(opts: Map<String, String>) {
    val catalog = JsonParser().parse(File(opts["catalog"] ?: error("--catalog required")).readText()).asJsonObject
    val tables = catalog.getAsJsonArray("tables").map { it.asJsonObject }
    val publications = catalog.getAsJsonArray("publications").map { it.asJsonObject }
    val subscriptions = catalog.getAsJsonArray("subscriptions").map { it.asJsonObject }.sortedBy { it.get("name").asString }
    val results = mutableListOf<LinkedHashMap<String, Any>>()
    for (sub in subscriptions) {
        val subName = sub.get("name").asString
        val pubName = sub.get("publication").asString
        val pub = publications.find { it.get("name").asString == pubName }
        for (target in sub.getAsJsonArray("targetTables").map { it.asJsonObject }.sortedBy { tableKey(it) }) {
            val tableName = tableKey(target)
            val subscriberColumns = target.getAsJsonArray("columns").map { it.asString }.sorted()
            val diagnostics = mutableListOf<LinkedHashMap<String, Any>>()
            val table = tables.find { tableKey(it) == tableName }
            val pubRef = pub?.getAsJsonArray("tables")?.map { it.asJsonObject }?.find { tableKey(it) == tableName }
            val publishedColumns = pubRef?.getAsJsonArray("columns")?.map { it.asString }?.sorted() ?: emptyList<String>()
            if (pub == null) {
                diagnostics.add(diag("missing_publication", "$pubName is not present in the publisher snapshot"))
            } else if (pubRef == null) {
                diagnostics.add(diag("missing_table", "$tableName is not in publication $pubName"))
            }
            if (table == null) {
                diagnostics.add(diag("missing_table", "$tableName is not present in the publisher schema"))
            } else {
                val schemaColumns = table.getAsJsonArray("columns").map { it.asJsonObject.get("name").asString }.toSet()
                val missingSchema = subscriberColumns.filter { !schemaColumns.contains(it) }
                if (missingSchema.isNotEmpty()) diagnostics.add(diag("missing_column", "${missingSchema.joinToString(", ")} absent from publisher table", missingSchema))
                if (pubRef != null && publishedColumns.isNotEmpty()) {
                    val missingPublished = subscriberColumns.filter { !publishedColumns.contains(it) }
                    if (missingPublished.isNotEmpty()) diagnostics.add(diag("unsafe_filter", "publication filter omits subscriber columns", missingPublished))
                    val missingPk = table.getAsJsonArray("columns").map { it.asJsonObject }.filter { it.get("primaryKey").asBoolean }.map { it.get("name").asString }.filter { !publishedColumns.contains(it) }
                    if (missingPk.isNotEmpty()) diagnostics.add(diag("primary_key_omitted", "publication filter omits primary key columns", missingPk))
                    if (table.get("replicaIdentity").asString == "full") diagnostics.add(diag("identity_filter_blocked", "$tableName uses REPLICA IDENTITY FULL with a column filter"))
                }
            }
            results.add(linkedMapOf(
                "subscription" to subName,
                "publication" to pubName,
                "table" to tableName,
                "status" to if (diagnostics.isEmpty()) "compatible" else "blocked",
                "publishedColumns" to publishedColumns,
                "subscriberColumns" to subscriberColumns,
                "diagnostics" to diagnostics
            ))
        }
    }
    val sorted = results.sortedWith(compareBy<LinkedHashMap<String, Any>> { it["subscription"].toString() }.thenBy { it["table"].toString() }.thenBy { it["publication"].toString() })
    writeJson(opts["out"] ?: error("--out required"), linkedMapOf(
        "summary" to linkedMapOf(
            "subscriptions" to subscriptions.size,
            "checkedTables" to sorted.size,
            "compatible" to sorted.count { it["status"] == "compatible" },
            "blocked" to sorted.count { it["status"] == "blocked" },
            "diagnostics" to sorted.sumBy { (it["diagnostics"] as List<*>).size }
        ),
        "results" to sorted
    ))
}

fun tableKey(obj: com.google.gson.JsonObject): String = obj.get("schema").asString + "." + obj.get("name").asString

fun diag(code: String, message: String, missing: List<String> = emptyList()): LinkedHashMap<String, Any> {
    val out = linkedMapOf<String, Any>("code" to code, "severity" to "blocking", "message" to message)
    if (missing.isNotEmpty()) out["missingColumns"] = missing.sorted()
    return out
}
'''
path.write_text(text)
PY

/app/build.sh
java -cp /app/build/pubgate.jar:/usr/share/java/gson.jar:/usr/share/java/sqlite-jdbc.jar:/usr/share/java/kotlin-stdlib.jar:/usr/share/java/kotlin-stdlib-jdk7.jar:/usr/share/java/kotlin-stdlib-jdk8.jar com.terminus.pubgate.MainKt parse --schema /app/input/publisher_schema.sql --publications /app/input/publications.sql --subscriptions /app/input/subscriptions.json --db /tmp/pubgate-smoke.db --out /tmp/pubgate-smoke.json
java -cp /app/build/pubgate.jar:/usr/share/java/gson.jar:/usr/share/java/sqlite-jdbc.jar:/usr/share/java/kotlin-stdlib.jar:/usr/share/java/kotlin-stdlib-jdk7.jar:/usr/share/java/kotlin-stdlib-jdk8.jar com.terminus.pubgate.MainKt validate --catalog /tmp/pubgate-smoke.json --out /tmp/pubgate-validation.json
