#!/bin/bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path

path = Path("/app/src/main/kotlin/com/terminus/pubgate/Main.kt")
text = path.read_text()
text = text.replace('"plan" -> { System.err.println("plan is not implemented in this stage"); kotlin.system.exitProcess(2) }', '"plan" -> plan(opts)')
if "fun plan(opts: Map<String, String>)" not in text:
    text += r'''

fun plan(opts: Map<String, String>) {
    val validation = JsonParser().parse(File(opts["validation"] ?: error("--validation required")).readText()).asJsonObject
    val actions = mutableListOf<LinkedHashMap<String, Any>>()
    for (result in validation.getAsJsonArray("results").map { it.asJsonObject }) {
        val sub = result.get("subscription").asString
        val pub = result.get("publication").asString
        val table = result.get("table").asString
        val published = result.getAsJsonArray("publishedColumns").map { it.asString }
        val subscriber = result.getAsJsonArray("subscriberColumns").map { it.asString }
        val widenColumns = linkedSetOf<String>()
        for (diag in result.getAsJsonArray("diagnostics").map { it.asJsonObject }) {
            val code = diag.get("code").asString
            when (code) {
                "missing_table" -> actions.add(action("add_table_to_publication", "blocking", sub, pub, table, subscriber, "ALTER PUBLICATION $pub ADD TABLE $table;", "table is absent from the publication"))
                "unsafe_filter", "primary_key_omitted" -> {
                    val missing = if (diag.has("missingColumns")) diag.getAsJsonArray("missingColumns").map { it.asString } else emptyList<String>()
                    widenColumns.addAll(missing)
                }
                "identity_filter_blocked" -> actions.add(action("review_replica_identity", "review", sub, pub, table, subscriber, "", "replica identity full tables with filters need manual migration review"))
                "missing_column" -> actions.add(action("review_schema_gap", "review", sub, pub, table, if (diag.has("missingColumns")) diag.getAsJsonArray("missingColumns").map { it.asString } else emptyList(), "", "subscriber expects columns absent from publisher schema"))
                "missing_publication" -> actions.add(action("create_publication_review", "review", sub, pub, table, subscriber, "", "publication is absent from the publisher snapshot"))
            }
        }
        if (widenColumns.isNotEmpty()) {
            val cols = (published + widenColumns).distinct().sorted()
            actions.add(action("widen_column_filter", "blocking", sub, pub, table, cols, "ALTER PUBLICATION $pub SET TABLE $table (${cols.joinToString(", ")});", "publication column filter must include required columns"))
        }
    }
    val deduped = actions.distinctBy { listOf(it["type"], it["subscription"], it["publication"], it["table"], it["sql"]).joinToString("|") }
    val sorted = deduped.sortedWith(compareBy<LinkedHashMap<String, Any>> { if (it["severity"] == "blocking") 0 else 1 }.thenBy { it["subscription"].toString() }.thenBy { it["publication"].toString() }.thenBy { it["table"].toString() }.thenBy { it["type"].toString() })
    writeJson(opts["out"] ?: error("--out required"), linkedMapOf(
        "summary" to linkedMapOf("actions" to sorted.size, "blockingActions" to sorted.count { it["severity"] == "blocking" }, "reviewActions" to sorted.count { it["severity"] == "review" }),
        "actions" to sorted
    ))
    val sqlPath = opts["sql"] ?: error("--sql required")
    File(sqlPath).parentFile?.mkdirs()
    val sqlLines = sorted.map { it["sql"].toString() }.filter { it.isNotBlank() }
    File(sqlPath).writeText(if (sqlLines.isEmpty()) "" else sqlLines.joinToString("\n") + "\n")
}

fun action(type: String, severity: String, sub: String, pub: String, table: String, columns: List<String>, sql: String, reason: String): LinkedHashMap<String, Any> =
    linkedMapOf("type" to type, "severity" to severity, "subscription" to sub, "publication" to pub, "table" to table, "columns" to columns.sorted(), "sql" to sql, "reason" to reason)
'''
path.write_text(text)
PY

/app/build.sh
java -cp /app/build/pubgate.jar:/usr/share/java/gson.jar:/usr/share/java/sqlite-jdbc.jar:/usr/share/java/kotlin-stdlib.jar:/usr/share/java/kotlin-stdlib-jdk7.jar:/usr/share/java/kotlin-stdlib-jdk8.jar com.terminus.pubgate.MainKt parse --schema /app/input/publisher_schema.sql --publications /app/input/publications.sql --subscriptions /app/input/subscriptions.json --db /tmp/pubgate-smoke.db --out /tmp/pubgate-smoke.json
java -cp /app/build/pubgate.jar:/usr/share/java/gson.jar:/usr/share/java/sqlite-jdbc.jar:/usr/share/java/kotlin-stdlib.jar:/usr/share/java/kotlin-stdlib-jdk7.jar:/usr/share/java/kotlin-stdlib-jdk8.jar com.terminus.pubgate.MainKt validate --catalog /tmp/pubgate-smoke.json --out /tmp/pubgate-validation.json
java -cp /app/build/pubgate.jar:/usr/share/java/gson.jar:/usr/share/java/sqlite-jdbc.jar:/usr/share/java/kotlin-stdlib.jar:/usr/share/java/kotlin-stdlib-jdk7.jar:/usr/share/java/kotlin-stdlib-jdk8.jar com.terminus.pubgate.MainKt plan --validation /tmp/pubgate-validation.json --out /tmp/pubgate-plan.json --sql /tmp/pubgate-plan.sql
