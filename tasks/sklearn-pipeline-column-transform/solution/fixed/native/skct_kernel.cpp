
#include <jni.h>
#include <string>
#include <fstream>
#include <sstream>
#include <vector>
#include <cmath>
static std::string jstr(JNIEnv* env, jstring s) {
    const char* c = env->GetStringUTFChars(s, nullptr);
    std::string out(c ? c : "");
    env->ReleaseStringUTFChars(s, c);
    return out;
}
static double extractNumAfter(const std::string& json, const std::string& key) {
    auto pos = json.find("\"" + key + "\":");
    if (pos == std::string::npos) return 0.0;
    pos = json.find(':', pos) + 1;
    while (pos < json.size() && (json[pos] == ' ')) pos++;
    return std::stod(json.substr(pos));
}
static std::string extractStrAfter(const std::string& json, const std::string& key) {
    auto pos = json.find("\"" + key + "\":\"");
    if (pos == std::string::npos) return "";
    pos = json.find('"', pos + key.size() + 3) + 1;
    auto end = json.find('"', pos);
    return json.substr(pos, end - pos);
}
static std::vector<std::string> parseExportOrder(const std::string& pipe) {
    std::vector<std::string> order;
    auto pos = pipe.find("\"export_order\"");
    if (pos == std::string::npos) return order;
    auto arrStart = pipe.find('[', pos);
    auto arrEnd = pipe.find(']', arrStart);
    if (arrStart == std::string::npos || arrEnd == std::string::npos) return order;
    std::string arr = pipe.substr(arrStart + 1, arrEnd - arrStart - 1);
    std::stringstream ss(arr);
    std::string token;
    while (std::getline(ss, token, ',')) {
        auto q1 = token.find('"');
        auto q2 = token.rfind('"');
        if (q1 == std::string::npos || q2 <= q1) continue;
        order.push_back(token.substr(q1 + 1, q2 - q1 - 1));
    }
    return order;
}
extern "C" JNIEXPORT jdouble JNICALL
Java_skct_jni_SkctNative_promoteSparseDtype(JNIEnv*, jclass, jint sparseVal, jdouble denseVal) {
    (void)denseVal;
    return static_cast<jdouble>(sparseVal);
}
extern "C" JNIEXPORT jdoubleArray JNICALL
Java_skct_jni_SkctNative_scoreRow(JNIEnv* env, jclass, jstring pipelinePath, jstring rowJson) {
    std::ifstream in(jstr(env, pipelinePath));
    std::stringstream buf; buf << in.rdbuf();
    std::string pipe = buf.str();
    std::string row = jstr(env, rowJson);
    double age = extractNumAfter(row, "age");
    double income = extractNumAfter(row, "income");
    double tenure = extractNumAfter(row, "tenure");
    std::string city = extractStrAfter(row, "city");
    auto agePos = pipe.find("\"age\"");
    auto incPos = pipe.find("\"income\"");
    double ageMean = extractNumAfter(pipe.substr(agePos), "mean");
    double ageStd = extractNumAfter(pipe.substr(agePos), "std");
    double incMean = extractNumAfter(pipe.substr(incPos), "mean");
    double incStd = extractNumAfter(pipe.substr(incPos), "std");
    if (ageStd == 0.0) ageStd = 1.0;
    if (incStd == 0.0) incStd = 1.0;
    double zAge = (age - ageMean) / ageStd;
    double zInc = (income - incMean) / incStd;
    std::vector<double> numeric = {zAge, zInc};
    std::vector<double> encoded;
    size_t catPos = pipe.find("\"city\"");
    if (catPos != std::string::npos) {
        size_t arrStart = pipe.find('[', catPos);
        size_t arrEnd = pipe.find(']', arrStart);
        std::string arr = pipe.substr(arrStart + 1, arrEnd - arrStart - 1);
        std::stringstream ss(arr);
        std::string token;
        while (std::getline(ss, token, ',')) {
            auto q1 = token.find('"'); auto q2 = token.rfind('"');
            if (q1 == std::string::npos || q2 <= q1) continue;
            std::string cat = token.substr(q1 + 1, q2 - q1 - 1);
            encoded.push_back(city == cat ? 1.0 : 0.0);
        }
    }
    std::vector<double> passthrough = {tenure};
    std::vector<double> vec;
    auto order = parseExportOrder(pipe);
    for (const auto& block : order) {
        if (block == "numeric") vec.insert(vec.end(), numeric.begin(), numeric.end());
        else if (block == "encoded") vec.insert(vec.end(), encoded.begin(), encoded.end());
        else if (block == "passthrough") vec.insert(vec.end(), passthrough.begin(), passthrough.end());
    }
    jdoubleArray out = env->NewDoubleArray((jsize)vec.size());
    env->SetDoubleArrayRegion(out, 0, (jsize)vec.size(), vec.data());
    return out;
}
