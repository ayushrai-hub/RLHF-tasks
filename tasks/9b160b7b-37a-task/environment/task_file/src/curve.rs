use crate::error::{err, Result};
use crate::json::Json;

#[derive(Clone, Copy, Debug)]
pub struct CurvePoint {
    pub cal_bp: f64,
    pub c14_bp: f64,
    pub sigma: f64,
}

pub fn parse_curve(value: &Json) -> Result<Vec<CurvePoint>> {
    let rows = value
        .as_array()
        .ok_or_else(|| crate::error::Error("curve must be an array".to_string()))?;
    if rows.len() < 2 {
        return err("curve must have at least two rows");
    }
    let mut curve = Vec::with_capacity(rows.len());
    let mut prev = f64::NEG_INFINITY;
    for row in rows {
        let cells = row
            .as_array()
            .ok_or_else(|| crate::error::Error("curve rows must be arrays".to_string()))?;
        if cells.len() != 3 {
            return err("curve rows must have three numbers");
        }
        let cal_bp = cells[0]
            .as_f64()
            .ok_or_else(|| crate::error::Error("bad cal_bp".to_string()))?;
        let c14_bp = cells[1]
            .as_f64()
            .ok_or_else(|| crate::error::Error("bad c14_bp".to_string()))?;
        let sigma = cells[2]
            .as_f64()
            .ok_or_else(|| crate::error::Error("bad sigma".to_string()))?;
        if !cal_bp.is_finite()
            || !c14_bp.is_finite()
            || !sigma.is_finite()
            || sigma <= 0.0
            || cal_bp <= prev
        {
            return err("invalid curve row");
        }
        prev = cal_bp;
        curve.push(CurvePoint {
            cal_bp,
            c14_bp,
            sigma,
        });
    }
    Ok(curve)
}

pub fn interpolate(curve: &[CurvePoint], cal_bp: f64) -> Result<CurvePoint> {
    if curve.len() < 2 || !cal_bp.is_finite() {
        return err("bad interpolation input");
    }
    let first = curve[0];
    let last = *curve.last().unwrap();
    if cal_bp < first.cal_bp || cal_bp > last.cal_bp {
        return err("calendar year outside curve");
    }
    if (cal_bp - first.cal_bp).abs() <= 0.0 {
        return Ok(first);
    }
    for pair in curve.windows(2) {
        let lo = pair[0];
        let hi = pair[1];
        if cal_bp <= hi.cal_bp {
            let span = hi.cal_bp - lo.cal_bp;
            if span <= 0.0 {
                return err("curve not strictly increasing");
            }
            let t = (cal_bp - lo.cal_bp) / span;
            return Ok(CurvePoint {
                cal_bp,
                c14_bp: lo.c14_bp + t * (hi.c14_bp - lo.c14_bp),
                sigma: lo.sigma + t * (hi.sigma - lo.sigma),
            });
        }
    }
    Ok(last)
}
