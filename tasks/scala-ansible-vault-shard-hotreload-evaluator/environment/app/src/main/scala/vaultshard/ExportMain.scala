package vaultshard

object ExportMain {
  def main(args: Array[String]): Unit = {
    var db = "/app/data/vault.db"
    var tenantId: String = null
    var out = "/app/output/vault-hotreload-audit.json"
    var i = 0
    while (i < args.length) {
      args(i) match {
        case "--db" =>
          i += 1; db = args(i)
        case "--tenant-id" =>
          i += 1; tenantId = args(i)
        case "--out" =>
          i += 1; out = args(i)
        case other => throw new RuntimeException(s"unknown arg: $other")
      }
      i += 1
    }
    if (tenantId == null) throw new RuntimeException("--tenant-id is required")
    Export.run(db, tenantId, out)
  }
}
