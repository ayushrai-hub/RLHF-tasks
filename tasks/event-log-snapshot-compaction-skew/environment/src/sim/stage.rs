use crate::sim::batch::Leg;

pub fn leg_count(legs: &[Leg]) -> usize {
    legs.len()
}

pub fn has_close(legs: &[Leg]) -> bool {
    legs.iter().any(|leg| matches!(leg, Leg::Close))
}

pub fn move_legs(legs: &[Leg]) -> usize {
    legs.iter().filter(|leg| matches!(leg, Leg::Move(_, _, _))).count()
}
