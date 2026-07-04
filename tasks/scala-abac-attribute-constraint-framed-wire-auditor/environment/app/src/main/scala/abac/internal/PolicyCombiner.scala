package abac.internal

object PolicyCombiner:
  def combine(prior: Option[Int], incoming: Int): Int =
    val p = prior.getOrElse(1)
    if p == 1 || incoming == 1 then 1 else 0
