package com.acme.rift

// Scala API sketch retained for the release workspace. The runtime provider is packaged for JVM ServiceLoader interoperability.
trait SchemaIndex {
  def canonicalize(descriptor: String): String
  def supports(descriptor: String): Boolean
}
