use crate::model::{RicochetResult, Vec3};

const DEG: f64 = 180.0 / std::f64::consts::PI;

fn round3(v: f64) -> f64 {
    (v * 1000.0).round() / 1000.0
}

fn angle_deg(a: Vec3, b: Vec3) -> f64 {
    let denom = a.magnitude() * b.magnitude();
    if denom <= 1e-12 {
        return 0.0;
    }
    let cos = (a.dot(b) / denom).clamp(-1.0, 1.0);
    round3(cos.acos() * DEG)
}

pub fn compute_ricochet(incident: Vec3, normal: Vec3) -> RicochetResult {
    let n = normal;
    let v = incident;
    let v_out = v.sub(n.scale(2.0 * v.dot(n)));
    RicochetResult {
        incident_angle_deg: angle_deg(v, n.scale(-1.0)),
        exit_angle_deg: angle_deg(v_out, n.scale(-1.0)),
        velocity_out: [v_out.x, v_out.y, v_out.z],
    }
}
