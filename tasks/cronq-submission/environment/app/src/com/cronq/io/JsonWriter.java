package com.cronq.io;

import java.util.List;

public final class JsonWriter {

    public static String success(String expr, String from, List<String> matches) {
        StringBuilder sb = new StringBuilder();
        sb.append("{");
        sb.append("\"ok\":true,");
        sb.append("\"expr\":").append(quote(expr)).append(",");
        sb.append("\"from\":").append(quote(from)).append(",");
        sb.append("\"matches\":[");
        for (int i = 0; i < matches.size(); i++) {
            if (i > 0) {
                sb.append(",");
            }
            sb.append(quote(matches.get(i)));
        }
        sb.append("]");
        sb.append("}");
        return sb.toString();
    }

    public static String error(String message) {
        return "{\"ok\":false,\"error\":" + quote(message) + "}";
    }

    private static String quote(String s) {
        StringBuilder sb = new StringBuilder("\"");
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"':
                    sb.append("\\\"");
                    break;
                case '\\':
                    sb.append("\\\\");
                    break;
                case '\n':
                    sb.append("\\n");
                    break;
                case '\r':
                    sb.append("\\r");
                    break;
                case '\t':
                    sb.append("\\t");
                    break;
                default:
                    sb.append(c);
            }
        }
        sb.append("\"");
        return sb.toString();
    }

    private JsonWriter() {
    }
}
