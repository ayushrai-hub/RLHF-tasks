package skct.jni;
public final class SkctNative {
    static { System.loadLibrary("skct_kernel"); }
    public static native double promoteSparseDtype(int sparseVal, double denseVal);
    public static native double[] scoreRow(String pipelinePath, String rowJson);
}
