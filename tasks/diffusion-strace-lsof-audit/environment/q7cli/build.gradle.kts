plugins {
    application
}

dependencies {
    implementation(project(":q7harvest"))
    implementation(project(":q8strace"))
    implementation(project(":q9lsof"))
    implementation(project(":r4policy"))
}

application {
    mainClass.set("io.q7desk.MainKt")
}

tasks.jar {
    archiveBaseName.set("trace-audit-cli")
    manifest {
        attributes["Main-Class"] = "io.q7desk.MainKt"
    }
    duplicatesStrategy = DuplicatesStrategy.EXCLUDE
    from({
        configurations.runtimeClasspath.get()
            .filter { it.name.endsWith("jar") }
            .map { if (it.isDirectory) it else zipTree(it) }
    })
}
