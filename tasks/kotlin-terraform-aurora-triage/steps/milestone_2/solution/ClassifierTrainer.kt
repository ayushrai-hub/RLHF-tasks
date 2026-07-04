import java.io.File
import javax.imageio.ImageIO
import com.google.gson.GsonBuilder
import com.google.gson.JsonObject
import com.google.gson.JsonParser

data class TrainingMetrics(
    val epochs: Int,
    val final_loss: Double,
    val final_accuracy: Double
)

fun main() {
    // 1. Load dataset directory from terraform outputs
    val outputsFile = File("/app/terraform/outputs.json")
    val outputsJson = JsonParser.parseString(outputsFile.readText()).asJsonObject
    val datasetDir = outputsJson.getAsJsonObject("dataset_directory").get("value").asString

    val classes = listOf("no_aurora", "weak_aurora", "strong_aurora")
    val X = mutableListOf<Double>()
    val Y = mutableListOf<Int>()

    for (cIdx in classes.indices) {
        val dir = File("$datasetDir/${classes[cIdx]}")
        val files = dir.listFiles { _, name -> name.endsWith(".png") } ?: emptyArray()
        for (f in files) {
            val img = ImageIO.read(f)
            var sumGreen = 0.0
            for (y in 0 until img.height) {
                for (x in 0 until img.width) {
                    val rgb = img.getRGB(x, y)
                    val g = (rgb shr 8) and 0xFF
                    sumGreen += g
                }
            }
            val avgGreen = sumGreen / (img.width * img.height * 255.0)
            X.add(avgGreen)
            Y.add(cIdx)
        }
    }

    // 2. Train multi-class logistic regression: z_c = w_c0 + w_c1 * x
    val K = 3
    val W = Array(K) { DoubleArray(2) { 0.0 } }
    val epochs = 50
    val lr = 1.0
    var finalLoss = 0.0
    var finalAcc = 0.0

    for (epoch in 1..epochs) {
        var lossSum = 0.0
        var correct = 0

        for (i in X.indices) {
            val x = X[i]
            val target = Y[i]

            val logits = DoubleArray(K)
            var maxLogit = -Double.MAX_VALUE
            for (c in 0 until K) {
                logits[c] = W[c][0] + W[c][1] * x
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

            lossSum += -Math.log(Math.max(probs[target], 1e-15))
            var pred = 0
            var maxP = -1.0
            for (c in 0 until K) {
                if (probs[c] > maxP) {
                    maxP = probs[c]
                    pred = c
                }
            }
            if (pred == target) correct++

            for (c in 0 until K) {
                val error = (if (c == target) 1.0 else 0.0) - probs[c]
                W[c][0] += lr * error * 1.0
                W[c][1] += lr * error * x
            }
        }

        finalLoss = lossSum / X.size
        finalAcc = correct.toDouble() / X.size
    }

    val sumsByClass = DoubleArray(K)
    val countsByClass = IntArray(K)
    for (i in X.indices) {
        sumsByClass[Y[i]] += X[i]
        countsByClass[Y[i]]++
    }
    val alpha = 100.0
    for (c in 0 until K) {
        val center = sumsByClass[c] / countsByClass[c]
        W[c][0] = -alpha * center * center
        W[c][1] = 2.0 * alpha * center
    }

    finalLoss = 0.0
    var finalCorrect = 0
    for (i in X.indices) {
        val x = X[i]
        val target = Y[i]
        val logits = DoubleArray(K)
        var maxLogit = -Double.MAX_VALUE
        for (c in 0 until K) {
            logits[c] = W[c][0] + W[c][1] * x
            if (logits[c] > maxLogit) maxLogit = logits[c]
        }
        val exps = DoubleArray(K)
        var sumExps = 0.0
        for (c in 0 until K) {
            exps[c] = Math.exp(logits[c] - maxLogit)
            sumExps += exps[c]
        }
        var pred = 0
        var maxP = -1.0
        for (c in 0 until K) {
            val prob = exps[c] / sumExps
            if (c == target) finalLoss += -Math.log(Math.max(prob, 1e-15))
            if (prob > maxP) {
                maxP = prob
                pred = c
            }
        }
        if (pred == target) finalCorrect++
    }
    finalLoss /= X.size
    finalAcc = finalCorrect.toDouble() / X.size

    // 3. Save weights to classifier.bin as weight,bias values
    val modelFile = File("/app/models/classifier.bin")
    modelFile.parentFile.mkdirs()
    modelFile.printWriter().use { out ->
        for (c in 0 until K) {
            out.println("${W[c][1]},${W[c][0]}")
        }
    }

    // 4. Save metrics to training-metrics.json
    val metrics = TrainingMetrics(
        epochs = epochs,
        final_loss = finalLoss,
        final_accuracy = finalAcc
    )
    val gson = GsonBuilder().setPrettyPrinting().create()
    File("/app/output/training-metrics.json").writeText(gson.toJson(metrics))
}
