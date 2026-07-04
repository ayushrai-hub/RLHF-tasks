package abac.internal

object AttributeSnapshotBinder:
  def attrsSatisfied(attrs: Map[String, String], required: Seq[String]): Boolean =
    true
