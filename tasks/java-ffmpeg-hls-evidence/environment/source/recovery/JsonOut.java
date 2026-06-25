package com.evidence.recovery;

import java.util.Map;
import java.util.TreeMap;

// Helper for compact, key-sorted JSON output. Intentionally minimal:
// only supports the subset of types the CLI emits.
public final class JsonOut {
  private JsonOut() {}

  public static String encode(Object node) {
    StringBuilder sb = new StringBuilder();
    write(sb, node);
    return sb.toString();
  }

  private static void write(StringBuilder sb, Object node) {
    if (node == null) {
      sb.append("null");
    } else if (node instanceof Boolean) {
      sb.append(((Boolean) node) ? "true" : "false");
    } else if (node instanceof Number) {
      sb.append(node.toString());
    } else if (node instanceof String) {
      escape(sb, (String) node);
    } else if (node instanceof Map) {
      writeMap(sb, (Map<?, ?>) node);
    } else if (node instanceof Iterable) {
      writeArray(sb, (Iterable<?>) node);
    } else {
      escape(sb, node.toString());
    }
  }

  private static void writeMap(StringBuilder sb, Map<?, ?> map) {
    TreeMap<String, Object> sorted = new TreeMap<>();
    for (Map.Entry<?, ?> e : map.entrySet()) {
      sorted.put(String.valueOf(e.getKey()), e.getValue());
    }
    sb.append('{');
    boolean first = true;
    for (Map.Entry<String, Object> e : sorted.entrySet()) {
      if (!first) sb.append(',');
      first = false;
      escape(sb, e.getKey());
      sb.append(':');
      write(sb, e.getValue());
    }
    sb.append('}');
  }

  private static void writeArray(StringBuilder sb, Iterable<?> items) {
    sb.append('[');
    boolean first = true;
    for (Object o : items) {
      if (!first) sb.append(',');
      first = false;
      write(sb, o);
    }
    sb.append(']');
  }

  private static void escape(StringBuilder sb, String s) {
    sb.append('"');
    for (int i = 0; i < s.length(); i++) {
      char c = s.charAt(i);
      switch (c) {
        case '"': sb.append("\\\""); break;
        case '\\': sb.append("\\\\"); break;
        case '\n': sb.append("\\n"); break;
        case '\r': sb.append("\\r"); break;
        case '\t': sb.append("\\t"); break;
        case '\b': sb.append("\\b"); break;
        case '\f': sb.append("\\f"); break;
        default:
          if (c < 0x20) {
            sb.append(String.format("\\u%04x", (int) c));
          } else {
            sb.append(c);
          }
      }
    }
    sb.append('"');
  }
}
