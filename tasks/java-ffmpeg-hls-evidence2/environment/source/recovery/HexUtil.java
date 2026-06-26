package com.evidence.recovery;

public final class HexUtil {
  private HexUtil() {}

  public static String hex(byte[] bytes) {
    StringBuilder sb = new StringBuilder(bytes.length * 2);
    for (byte b : bytes) {
      sb.append(String.format("%02x", b & 0xff));
    }
    return sb.toString();
  }

  public static byte[] unhex(String s) {
    if (s.length() % 2 != 0) {
      throw new IllegalArgumentException("odd-length hex");
    }
    byte[] out = new byte[s.length() / 2];
    for (int i = 0; i < out.length; i++) {
      out[i] = (byte) Integer.parseInt(s.substring(i * 2, i * 2 + 2), 16);
    }
    return out;
  }
}
