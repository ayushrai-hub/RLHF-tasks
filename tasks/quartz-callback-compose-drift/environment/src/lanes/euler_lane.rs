use crate::qz::n2::q2::euler_forward;

pub fn euler_step(y: f64, dt: f64) -> f64 {
    euler_forward(y, dt)
}
