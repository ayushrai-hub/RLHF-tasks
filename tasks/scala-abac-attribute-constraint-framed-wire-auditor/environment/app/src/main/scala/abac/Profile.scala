package abac

import java.nio.file.{Files, Paths}
import scala.util.Using

final case class Profile(
    abacEpochBase: Long,
    requiredAttrs: Seq[String],
    defaultCombiner: String
)

object Profile:
  private val path = "/app/config/abac-policy-profile.json"

  def load(): Profile =
    val raw = Files.readString(Paths.get(path))
    val epoch = fieldLong(raw, "abac_epoch_base")
    val combiner = fieldStr(raw, "default_combiner")
    val req = parseRequired(raw)
    Profile(epoch, req, combiner)

  private def fieldStr(json: String, key: String): String =
    val re = ("\"" + key + "\"\\s*:\\s*\"([^\"]*)\"").r
    re.findFirstMatchIn(json).map(_.group(1)).getOrElse("")

  private def fieldLong(json: String, key: String): Long =
    val re = ("\"" + key + "\"\\s*:\\s*(\\d+)").r
    re.findFirstMatchIn(json).map(_.group(1).toLong).getOrElse(0L)

  private def parseRequired(json: String): Seq[String] =
    val re = """"required_attrs"\s*:\s*\[([^\]]*)\]""".r
    re.findFirstMatchIn(json) match
      case None => Seq.empty
      case Some(m) =>
        """"([^"]+)"""".r.findAllMatchIn(m.group(1)).map(_.group(1)).toSeq
