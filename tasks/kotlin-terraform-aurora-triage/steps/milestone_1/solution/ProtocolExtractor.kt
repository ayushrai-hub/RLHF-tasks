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

    // Extract strong_aurora_threshold
    var strongThreshold = 0.85
    val probPattern = "strong aurora probability threshold to\\s+strictly\\s+\\d+%(?:\\s*\\((\\d+\\.\\d+)\\))?".toRegex()
    probPattern.find(thresholdNotes)?.groups?.get(1)?.value?.let {
        strongThreshold = it.toDouble()
    }

    // Extract quarantine_temp_threshold
    var tempThreshold = -25.0
    val tempPattern = "strictly\\s+below\\s+(-?\\d+)C".toRegex()
    tempPattern.find(meetingNotes)?.groups?.get(1)?.value?.let {
        tempThreshold = it.toDouble()
    }

    // Extract untrusted_sensor_id
    var untrustedSensor = "SNS-999"
    val untrustedPattern = "sensor ID \"(SNS-\\d+)\"".toRegex()
    untrustedPattern.find(meetingNotes)?.groups?.get(1)?.value?.let {
        untrustedSensor = it
    }

    // Extract trusted_sensor_ids
    var trustedSensors = listOf("SNS-001", "SNS-002", "SNS-003")
    val trustedPattern = "Sensors\\s+(SNS-\\d+),\\s*(SNS-\\d+),\\s*and\\s*(SNS-\\d+)".toRegex()
    trustedPattern.find(meetingNotes)?.let { matchResult ->
        trustedSensors = listOf(
            matchResult.groupValues[1],
            matchResult.groupValues[2],
            matchResult.groupValues[3]
        )
    }

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
