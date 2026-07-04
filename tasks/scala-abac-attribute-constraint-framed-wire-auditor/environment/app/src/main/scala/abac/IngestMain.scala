package abac

object IngestMain:
  def main(args: Array[String]): Unit =
    val opts = parseArgs(args)
    val db = opts.getOrElse("db", "/app/data/abac.db")
    val batch = opts.get("batch") match
      case Some(v) => v
      case None =>
        System.err.println("usage: abac-ingest --db <path> --batch <abwf>")
        sys.exit(2)
    val conn = Store.connect(db)
    try
      Store.migrate(conn)
      val profile = Profile.load()
      Ingest.ingestFile(conn, batch, profile)
      println("ingested")
    catch
      case e: Throwable =>
        conn.rollback()
        System.err.println("ingest failed: " + e.getMessage)
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
