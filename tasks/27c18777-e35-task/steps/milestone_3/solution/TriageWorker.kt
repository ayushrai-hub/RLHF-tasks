import java.io.File
import javax.imageio.ImageIO
import com.google.gson.GsonBuilder
import com.google.gson.JsonObject
import com.google.gson.JsonParser

data class PredictionResult(
    val frame_id: String,
    val aurora_class: String,
    val probability: Double,
    val action: String,
    val flagged: Boolean
)

data class RunSummary(
    val total_processed: Int,
    val escalated_count: Int,
    val quarantined_count: Int,
    val archived_count: Int
)

fun main() {
    // 1. Read /app/terraform/outputs.json
    val outputsFile = File("/app/terraform/outputs.json")
    val outputsJson = JsonParser.parseString(outputsFile.readText()).asJsonObject
    val incomingDir = File(outputsJson.getAsJsonObject("incoming_directory").get("value").asString)
    val predictionsDir = File(outputsJson.getAsJsonObject("predictions_directory").get("value").asString)
    predictionsDir.mkdirs()
    predictionsDir.listFiles { _, name -> name.endsWith("_result.json") }?.forEach { it.delete() }

    // 2. Read /app/output/protocol-decisions.json
    val decisionsFile = File("/app/output/protocol-decisions.json")
    val decisionsJson = JsonParser.parseString(decisionsFile.readText()).asJsonObject
    val strongAuroraThreshold = decisionsJson.get("strong_aurora_threshold").asDouble
    val quarantineTempThreshold = decisionsJson.get("quarantine_temp_threshold").asDouble
    val untrustedSensorId = decisionsJson.get("untrusted_sensor_id").asString

    // 3. Load classifier weights from /app/models/classifier.bin
    val modelFile = File("/app/models/classifier.bin")
    val K = 3
    val W = Array(K) { DoubleArray(2) }
    val modelLines = modelFile.readLines()
    for (c in 0 until K) {
        val parts = modelLines[c].split(",")
        W[c][0] = parts[1].toDouble()
        W[c][1] = parts[0].toDouble()
    }

    // 4. Find all PNG files in incoming directory
    val pngFiles = incomingDir.listFiles { _, name -> name.endsWith(".png") } ?: emptyArray()
    pngFiles.sortBy { it.name }

    var totalProcessed = 0
    var escalatedCount = 0
    var quarantinedCount = 0
    var archivedCount = 0

    val gson = GsonBuilder().setPrettyPrinting().create()
    val classes = listOf("no_aurora", "weak_aurora", "strong_aurora")

    for (pngFile in pngFiles) {
        val frameId = pngFile.nameWithoutExtension
        val metaFile = File(incomingDir, "$frameId.json")
        if (!metaFile.exists()) continue

        // Parse metadata JSON
        val metaJson = JsonParser.parseString(metaFile.readText()).asJsonObject
        val sensorId = metaJson.get("sensor_id").asString
        val temperature = metaJson.get("temperature").asDouble

        // Classify PNG
        val img = ImageIO.read(pngFile)
        var sumGreen = 0.0
        for (y in 0 until img.height) {
            for (x in 0 until img.width) {
                val rgb = img.getRGB(x, y)
                val g = (rgb shr 8) and 0xFF
                sumGreen += g
            }
        }
        val avgGreen = sumGreen / (img.width * img.height * 255.0)

        // Compute probabilities
        val logits = DoubleArray(K)
        var maxLogit = -Double.MAX_VALUE
        for (c in 0 until K) {
            logits[c] = W[c][0] + W[c][1] * avgGreen
            if (logits[c] > maxLogit) maxLogit = logits[c]
        }

        val exps = DoubleArray(K)
        var sumExps = 0.0
        for (c in 0 until K) {
            exps[c] = Math.exp(logits[c] - maxLogit)
            sumExps += exps[c]
        }

        val probs = DoubleArray(K)
        for (c in 0 until K) {
            probs[c] = exps[c] / sumExps
        }

        var predClassIdx = 0
        var maxP = -1.0
        for (c in 0 until K) {
            if (probs[c] > maxP) {
                maxP = probs[c]
                predClassIdx = c
            }
        }

        val auroraClass = classes[predClassIdx]

        // Apply rules to decide target action
        var action = "archive"
        var flagged = false

        if (sensorId == untrustedSensorId) {
            action = "quarantine"
            flagged = true
        } else {
            if (probs[2] >= strongAuroraThreshold) {
                action = "escalate"
                flagged = true
            } else if (auroraClass == "weak_aurora" && temperature < quarantineTempThreshold) {
                action = "quarantine"
                flagged = true
            }
        }

        // Increment counts
        totalProcessed++
        when (action) {
            "escalate" -> escalatedCount++
            "quarantine" -> quarantinedCount++
            else -> archivedCount++
        }

        // Save result
        val result = PredictionResult(
            frame_id = frameId,
            aurora_class = auroraClass,
            probability = maxP,
            action = action,
            flagged = flagged
        )
        val resultJsonStr = gson.toJson(result)
        val resultFile = File(predictionsDir, "${frameId}_result.json")
        resultFile.writeText(resultJsonStr)
    }

    // Write run_summary.json
    val summary = RunSummary(
        total_processed = totalProcessed,
        escalated_count = escalatedCount,
        quarantined_count = quarantinedCount,
        archived_count = archivedCount
    )
    val summaryJsonStr = gson.toJson(summary)
    File("/app/output/run_summary.json").writeText(summaryJsonStr)
}
