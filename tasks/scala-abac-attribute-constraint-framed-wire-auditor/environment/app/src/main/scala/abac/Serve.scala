package abac

import java.net.{InetSocketAddress, ServerSocket, Socket}
import java.nio.charset.StandardCharsets
import java.sql.Connection
import abac.internal.{AttributeSnapshotBinder, ProbeMergeCoordinator}

object Serve:
  def run(conn: Connection, listen: String, profile: Profile): Unit =
    val parts = listen.split(":")
    val host = parts(0)
    val port = parts(1).toInt
    val ss = new ServerSocket()
    ss.bind(new InetSocketAddress(host, port))
    try
      while true do
        val sock = ss.accept()
        try handle(conn, sock, profile)
        finally sock.close()
    finally ss.close()

  private def handle(conn: Connection, sock: Socket, profile: Profile): Unit =
    val in = sock.getInputStream
    val out = sock.getOutputStream
    val req = new String(in.readAllBytes(), StandardCharsets.UTF_8)
    val lines = req.split("\r\n")
    if lines.isEmpty then return
    val parts = lines(0).split(" ")
    if parts.length < 2 then return
    val method = parts(0)
    val path = parts(1)
    if method == "GET" && path == "/health" then
      writeResponse(out, 200, """{"status":"ok"}""")
      return
    if method == "POST" && path.startsWith("/v1/tenants/") && path.endsWith("/probe") then
      val tenantId = path.split("/")(3)
      val body = lines.dropWhile(_ != "").drop(1).mkString("\n")
      val reqAttrs = parseJsonAttrs(body)
      val policyId = reqAttrs.getOrElse("policy_id", "default")
      val merged = ProbeMergeCoordinator.mergeForProbe(conn, tenantId, policyId, reqAttrs)
      val decision = if AttributeSnapshotBinder.attrsSatisfied(merged, profile.requiredAttrs) then 1 else 0
      writeResponse(out, 200, s"""{"tenant_id":"$tenantId","effective_decision":$decision}""")
      return
    writeResponse(out, 404, """{"error":"not found"}""")

  private def parseJsonAttrs(body: String): Map[String, String] =
    val m = scala.collection.mutable.Map.empty[String, String]
    val re = """"([^"]+)"\s*:\s*"([^"]*)"""".r
    re.findAllMatchIn(body).foreach { mm =>
      m(mm.group(1)) = mm.group(2)
    }
    m.toMap

  private def writeResponse(out: java.io.OutputStream, code: Int, body: String): Unit =
    val status = if code == 200 then "OK" else "Error"
    val resp =
      s"HTTP/1.1 $code $status\r\nContent-Type: application/json\r\nContent-Length: ${body.length}\r\n\r\n$body"
    out.write(resp.getBytes(StandardCharsets.UTF_8))
