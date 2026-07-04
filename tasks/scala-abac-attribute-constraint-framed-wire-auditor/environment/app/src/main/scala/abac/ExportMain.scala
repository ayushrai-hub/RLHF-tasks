package abac

object ExportMain:
  def main(args: Array[String]): Unit =
    val opts = parseArgs(args)
    val db = opts.getOrElse("db", "/app/data/abac.db")
    val tenant = opts.getOrElse("tenant", "TEN")
    val out = opts.getOrElse("out", "/app/output/abac-constraint-audit.json")
    val conn = Store.connect(db)
    try
      Store.migrate(conn)
      val profile = Profile.load()
      Export.exportTenant(conn, tenant, out, profile)
      println("exported")
    catch
      case e: Throwable =>
        System.err.println("export failed: " + e.getMessage)
        sys.exit(1)
    finally conn.close()

  private def parseArgs(args: Array[String]): Map[String, String] =
    val m = scala.collection.mutable.Map.empty[String, String]
    var i = 0
    while i < args.length do
      val a = args(i)
      if a.startsWith("--") && i + 1 < args.length then
        m(a.drop(2)) = args(i + 1)
        i += 2
      else i += 1
    m.toMap
