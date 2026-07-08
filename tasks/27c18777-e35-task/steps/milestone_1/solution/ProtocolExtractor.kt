import java.io.File
import com.google.gson.GsonBuilder

data class ProtocolDecisions(
    val strong_aurora_threshold: Double,
    val quarantine_temp_threshold: Double,
    val untrusted_sensor_id: String,
    val trusted_sensor_ids: List<String>
)

fun main() {
    val archiveFile = File("/app/docs/incident-archive.txt")
    val content = archiveFile.readText()
    val meetingNotes = content.substringAfter("3. MEETING NOTES: TEMPERATURE ALERTS & SENSORS")
        .substringBefore("4. EMAIL THREAD: TARGET ACTION STANDARDIZATION")
    val thresholdNotes = content.substringAfter("2. DISCUSSION ON CLASSIFIER THRESHOLDS")
        .substringBefore("3. MEETING NOTES: TEMPERATURE ALERTS & SENSORS")

    val probPattern = "strong aurora probability threshold to\\s+strictly\\s+\\d+%(?:\\s*\\((\\d+\\.\\d+)\\))?".toRegex()
    val strongThreshold = probPattern.find(thresholdNotes)
        ?.groups
        ?.get(1)
        ?.value
        ?.toDouble()
        ?: error("Missing approved strong aurora threshold")

    val tempPattern = "strictly\\s+below\\s+(-?\\d+)C".toRegex()
    val tempThreshold = tempPattern.find(meetingNotes)
        ?.groups
        ?.get(1)
        ?.value
        ?.toDouble()
        ?: error("Missing approved quarantine temperature threshold")

    val untrustedPattern = "sensor ID \"(SNS-\\d+)\"".toRegex()
    val untrustedSensor = untrustedPattern.find(meetingNotes)
        ?.groups
        ?.get(1)
        ?.value
        ?: error("Missing approved untrusted sensor ID")

    val trustedPattern = "Sensors\\s+(SNS-\\d+),\\s*(SNS-\\d+),\\s*and\\s*(SNS-\\d+)".toRegex()
    val trustedSensors = trustedPattern.find(meetingNotes)
        ?.let { matchResult ->
            listOf(
                matchResult.groupValues[1],
                matchResult.groupValues[2],
                matchResult.groupValues[3]
            )
        }
        ?: error("Missing approved trusted sensor list")

    val decisions = ProtocolDecisions(
        strong_aurora_threshold = strongThreshold,
        quarantine_temp_threshold = tempThreshold,
        untrusted_sensor_id = untrustedSensor,
        trusted_sensor_ids = trustedSensors
    )

    val gson = GsonBuilder().setPrettyPrinting().create()
    val jsonStr = gson.toJson(decisions)

    val outputFile = File("/app/output/protocol-decisions.json")
    outputFile.parentFile.mkdirs()
    outputFile.writeText(jsonStr)
}
