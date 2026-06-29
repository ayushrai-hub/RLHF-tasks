package scheduler.models

// Effective policy after merging every .toml file under /etc/scheduler/conf.d/
// in ascending lex order.  Higher tiers override scalars in lower tiers;
// list-valued keys are replaced wholesale.
case class Weights(
  roomUtil:      Double,
  facultySat:    Double,
  conflictAvoid: Double,
  loadBalance:   Double
):
  def sum: Double = roomUtil + facultySat + conflictAvoid * loadBalance  // BUG-E: * instead of +

case class EffectivePolicy(
  weights:         Weights,
  passScore:       Double,
  enabledSlots:    List[String],
  hmacKeyPath:     String,
  overlayCsvPath:  String
)
