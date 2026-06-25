package com.evidence.recovery;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

// Minimal JSON parser sufficient for /app/data/wrapped_keys.json,
// recovery_config.json, and the small fixture files. Not a full RFC
// 8259 parser; rejects exotic escapes.
public final class MiniJson {
  private MiniJson() {}

  public static Object parse(String s) {
    Parser p = new Parser(s);
    p.skipWs();
    Object out = p.value();
    p.skipWs();
    if (p.i != s.length()) {
      throw new IllegalStateException("trailing data at offset " + p.i);
    }
    return out;
  }

  private static class Parser {
    final String s;
    int i;

    Parser(String s) {
      this.s = s;
    }

    Object value() {
      skipWs();
      char c = s.charAt(i);
      if (c == '{') return object();
      if (c == '[') return array();
      if (c == '"') return string();
      if (c == 't' || c == 'f') return bool();
      if (c == 'n') return nullLit();
      return number();
    }

    Map<String, Object> object() {
      expect('{');
      Map<String, Object> m = new LinkedHashMap<>();
      skipWs();
      if (peek() == '}') { i++; return m; }
      while (true) {
        skipWs();
        String key = string();
        skipWs();
        expect(':');
        Object v = value();
        m.put(key, v);
        skipWs();
        char c = s.charAt(i++);
        if (c == '}') return m;
        if (c != ',') throw new IllegalStateException("expected , or }");
      }
    }

    List<Object> array() {
      expect('[');
      List<Object> a = new ArrayList<>();
      skipWs();
      if (peek() == ']') { i++; return a; }
      while (true) {
        a.add(value());
        skipWs();
        char c = s.charAt(i++);
        if (c == ']') return a;
        if (c != ',') throw new IllegalStateException("expected , or ]");
      }
    }

    String string() {
      expect('"');
      StringBuilder sb = new StringBuilder();
      while (i < s.length()) {
        char c = s.charAt(i++);
        if (c == '"') return sb.toString();
        if (c == '\\') {
          char esc = s.charAt(i++);
          switch (esc) {
            case '"': sb.append('"'); break;
            case '\\': sb.append('\\'); break;
            case '/': sb.append('/'); break;
            case 'n': sb.append('\n'); break;
            case 'r': sb.append('\r'); break;
            case 't': sb.append('\t'); break;
            case 'b': sb.append('\b'); break;
            case 'f': sb.append('\f'); break;
            case 'u': {
              String hex = s.substring(i, i + 4);
              i += 4;
              sb.append((char) Integer.parseInt(hex, 16));
              break;
            }
            default: throw new IllegalStateException("bad escape \\" + esc);
          }
        } else {
          sb.append(c);
        }
      }
      throw new IllegalStateException("unterminated string");
    }

    Boolean bool() {
      if (s.startsWith("true", i)) { i += 4; return Boolean.TRUE; }
      if (s.startsWith("false", i)) { i += 5; return Boolean.FALSE; }
      throw new IllegalStateException("expected bool at " + i);
    }

    Object nullLit() {
      if (s.startsWith("null", i)) { i += 4; return null; }
      throw new IllegalStateException("expected null at " + i);
    }

    Object number() {
      int start = i;
      if (peek() == '-') i++;
      while (i < s.length() && (Character.isDigit(s.charAt(i)) || ".eE+-".indexOf(s.charAt(i)) >= 0)) i++;
      String tok = s.substring(start, i);
      if (tok.indexOf('.') < 0 && tok.indexOf('e') < 0 && tok.indexOf('E') < 0) {
        return Long.parseLong(tok);
      }
      return Double.parseDouble(tok);
    }

    void expect(char c) {
      if (s.charAt(i) != c) throw new IllegalStateException("expected " + c + " at " + i);
      i++;
    }

    char peek() {
      return s.charAt(i);
    }

    void skipWs() {
      while (i < s.length() && Character.isWhitespace(s.charAt(i))) i++;
    }
  }
}
