
#include <jni.h>
extern "C" JNIEXPORT jdouble JNICALL
Java_skct_jni_SkctNative_promoteSparseDtype(JNIEnv*, jclass, jint sparseVal, jdouble denseVal) {
    if (denseVal == 0.0) return (jdouble)sparseVal;
    return (jdouble)sparseVal / denseVal;
}
extern "C" JNIEXPORT jdoubleArray JNICALL
Java_skct_jni_SkctNative_scoreRow(JNIEnv* env, jclass, jstring, jstring) {
    jdoubleArray out = env->NewDoubleArray(1);
    jdouble v = 0.0;
    env->SetDoubleArrayRegion(out, 0, 1, &v);
    return out;
}
