package vaultshard

/** Minimal JSON support for the backup audit CLI. */
object Json {

  sealed trait JValue
  final case class JStr(s: String) extends JValue
  final case class JInt(v: Long) extends JValue
  final case class JArr(items: List[JValue]) extends JValue
  final case class JObj(fields: List[(String, JValue)]) extends JValue

  def quote(s: String): String = {
    val sb = new StringBuilder
    sb.append('"')
    var i = 0
    while (i < s.length) {
      val c = s.charAt(i)
      c match {
        case '"'  => sb.append("\\\"")
        case '\\' => sb.append("\\\\")
        case '\n' => sb.append("\\n")
        case '\r' => sb.append("\\r")
        case '\t' => sb.append("\\t")
        case '\b' => sb.append("\\b")
        case '\f' => sb.append("\\f")
        case _ =>
          if (c < 0x20) sb.append("\\u%04x".format(c.toInt))
          else sb.append(c)
      }
      i += 1
    }
    sb.append('"')
    sb.toString
  }

  def compact(v: JValue): String = v match {
    case JStr(s)  => quote(s)
    case JInt(n)  => n.toString
    case JArr(it) => "[" + it.map(compact).mkString(",") + "]"
    case JObj(fs) => "{" + fs.map { case (k, vv) => quote(k) + ":" + compact(vv) }.mkString(",") + "}"
  }

  def pretty(v: JValue, indent: Int = 0): String = v match {
    case JStr(s)      => quote(s)
    case JInt(n)      => n.toString
    case JArr(Nil)    => "[]"
    case JObj(Nil)    => "{}"
    case JArr(items) =>
      val pad = " " * (indent + 2)
      val inner = items.map(it => pad + pretty(it, indent + 2)).mkString(",\n")
      "[\n" + inner + "\n" + (" " * indent) + "]"
    case JObj(fs) =>
      val pad = " " * (indent + 2)
      val inner = fs.map { case (k, vv) => pad + quote(k) + ": " + pretty(vv, indent + 2) }.mkString(",\n")
      "{\n" + inner + "\n" + (" " * indent) + "}"
  }

  def parse(s: String): JValue = {
    val p = new Parser(s)
    p.skipWs()
    val v = p.parseValue()
    p.skipWs()
    if (!p.atEnd) throw new JsonError("trailing characters after JSON value")
    v
  }

  final class JsonError(msg: String) extends RuntimeException(msg)

  private final class Parser(s: String) {
    private var i = 0

    def atEnd: Boolean = i >= s.length

    def skipWs(): Unit =
      while (i < s.length && Character.isWhitespace(s.charAt(i))) i += 1

    def parseValue(): JValue = {
      skipWs()
      if (i >= s.length) throw new JsonError("unexpected end of input")
      s.charAt(i) match {
        case '{' => parseObj()
        case '[' => parseArr()
        case '"' => JStr(parseStr())
        case c if c == '-' || (c >= '0' && c <= '9') => parseNum()
        case c => throw new JsonError(s"unexpected character '$c'")
      }
    }

    private def parseObj(): JObj = {
      expect('{')
      skipWs()
      val buf = scala.collection.mutable.ListBuffer.empty[(String, JValue)]
      if (peek() == '}') { i += 1; return JObj(Nil) }
      var more = true
      while (more) {
        skipWs()
        val key = parseStr()
        skipWs()
        expect(':')
        val value = parseValue()
        buf += (key -> value)
        skipWs()
        peek() match {
          case ',' => i += 1
          case '}' => i += 1; more = false
          case c   => throw new JsonError(s"expected ',' or '}' but found '$c'")
        }
      }
      JObj(buf.toList)
    }

    private def parseArr(): JArr = {
      expect('[')
      skipWs()
      val buf = scala.collection.mutable.ListBuffer.empty[JValue]
      if (peek() == ']') { i += 1; return JArr(Nil) }
      var more = true
      while (more) {
        val value = parseValue()
        buf += value
        skipWs()
        peek() match {
          case ',' => i += 1
          case ']' => i += 1; more = false
          case c   => throw new JsonError(s"expected ',' or ']' but found '$c'")
        }
      }
      JArr(buf.toList)
    }

    private def parseStr(): String = {
      expect('"')
      val sb = new StringBuilder
      var done = false
      while (!done) {
        if (i >= s.length) throw new JsonError("unterminated string")
        val c = s.charAt(i); i += 1
        c match {
          case '"' => done = true
          case '\\' =>
            if (i >= s.length) throw new JsonError("unterminated escape")
            val e = s.charAt(i); i += 1
            e match {
              case '"'  => sb.append('"')
              case '\\' => sb.append('\\')
              case '/'  => sb.append('/')
              case 'n'  => sb.append('\n')
              case 'r'  => sb.append('\r')
              case 't'  => sb.append('\t')
              case 'b'  => sb.append('\b')
              case 'f'  => sb.append('\f')
              case 'u'  =>
                if (i + 4 > s.length) throw new JsonError("bad unicode escape")
                val hex = s.substring(i, i + 4); i += 4
                sb.append(Integer.parseInt(hex, 16).toChar)
              case other => throw new JsonError(s"bad escape '\\$other'")
            }
          case other => sb.append(other)
        }
      }
      sb.toString
    }

    private def parseNum(): JInt = {
      val start = i
      if (peek() == '-') i += 1
      while (i < s.length && s.charAt(i) >= '0' && s.charAt(i) <= '9') i += 1
      if (i < s.length && (s.charAt(i) == '.' || s.charAt(i) == 'e' || s.charAt(i) == 'E'))
        throw new JsonError("non-integer numbers are not supported")
      val text = s.substring(start, i)
      if (text.isEmpty || text == "-") throw new JsonError("invalid number")
      JInt(text.toLong)
    }

    private def peek(): Char =
      if (i >= s.length) throw new JsonError("unexpected end of input") else s.charAt(i)

    private def expect(c: Char): Unit = {
      skipWs()
      if (i >= s.length || s.charAt(i) != c)
        throw new JsonError(s"expected '$c'")
      i += 1
    }
  }
}
