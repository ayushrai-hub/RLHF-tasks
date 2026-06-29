scalaVersion := "3.3.4"
name := "course-scheduler"
version := "1.0.0"

libraryDependencies ++= Seq(
  "com.lihaoyi" %% "ujson" % "3.3.0",
  "com.lihaoyi" %% "upickle" % "3.3.0"
)

assembly / assemblyJarName := "scheduler.jar"
assembly / assemblyMergeStrategy := {
  case PathList("META-INF", xs @ _*) => MergeStrategy.discard
  case x => MergeStrategy.first
}
