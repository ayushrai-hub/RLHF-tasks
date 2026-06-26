package vaultshard

object IngestMain {
  def main(args: Array[String]): Unit = {
    var db = "/app/data/vault.db"
    var bundle: String = null
    var i = 0
    while (i < args.length) {
      args(i) match {
        case "--db" =>
          i += 1; db = args(i)
        case "--bundle" =>
          i += 1; bundle = args(i)
        case other => throw new RuntimeException(s"unknown arg: $other")
      }
      i += 1
    }
    if (bundle == null) throw new RuntimeException("--bundle is required")
    Ingest.run(db, bundle)
  }
}
