package abac

object ServeMain:
  def main(args: Array[String]): Unit =
    val opts = parseArgs(args)
    val listen = opts.getOrElse("listen", sys.env.getOrElse("ABAC_LISTEN", "127.0.0.1:8091"))
    val db = opts.getOrElse("db", sys.env.getOrElse("ABAC_DB", "/app/data/abac.db"))
    val conn = Store.connect(db)
    try
      Store.migrate(conn)
      val profile = Profile.load()
      Serve.run(conn, listen, profile)
    catch
      case e: Throwable =>
        System.err.println("serve failed: " + e.getMessage)
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
