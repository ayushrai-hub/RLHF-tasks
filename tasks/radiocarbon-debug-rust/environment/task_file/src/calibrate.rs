use crate::curve::{interpolate, CurvePoint};
use crate::error::{err, Result};

#[derive(Clone, Debug)]
pub struct CalibrationInput {
    pub curve: Vec<CurvePoint>,
    pub lab_age_bp: f64,
    pub lab_sigma: f64,
    pub reservoir_age: f64,
    pub reservoir_sigma: f64,
    pub start_cal_bp: f64,
    pub end_cal_bp: f64,
    pub step: f64,
}

#[derive(Clone, Debug)]
pub struct CalibrationPoint {
    pub cal_bp: f64,
    pub probability: f64,
}

#[derive(Clone, Debug)]
pub struct Calibration {
    pub points: Vec<CalibrationPoint>,
    pub mean_cal_bp: f64,
    pub mode_cal_bp: f64,
}

#[derive(Clone, Debug)]
pub struct IntervalReport {
    pub level: f64,
    pub ranges: Vec<[f64; 2]>,
    pub mass: f64,
}

#[derive(Clone, Debug)]
pub struct CurveModel {
    pub weight: f64,
    pub curve: Vec<CurvePoint>,
}

#[derive(Clone, Debug)]
pub struct CurveMixtureResult {
    pub joint: Vec<[f64; 3]>,
    pub points: Vec<CalibrationPoint>,
    pub mean_cal_bp: f64,
    pub mode_cal_bp: f64,
    pub curve_posteriors: Vec<[f64; 2]>,
    pub intervals: Vec<IntervalReport>,
}

#[derive(Clone, Debug)]
pub struct Determination {
    pub age_bp: f64,
    pub sigma: f64,
    pub reservoir_age: f64,
    pub reservoir_sigma: f64,
}

#[derive(Clone, Debug)]
pub struct Combined {
    pub age_bp: f64,
    pub sigma: f64,
    pub chi_square: f64,
    pub dof: usize,
    pub passes: bool,
}

#[derive(Clone, Debug)]
pub struct SequenceSample {
    pub lab_age_bp: f64,
    pub lab_sigma: f64,
    pub reservoir_age: f64,
    pub reservoir_sigma: f64,
}

#[derive(Clone, Debug)]
pub struct SequenceMarginal {
    pub sample: usize,
    pub calibration: Calibration,
    pub intervals: Vec<IntervalReport>,
}

#[derive(Clone, Debug)]
pub struct SequenceResult {
    pub order_probability: f64,
    pub marginals: Vec<SequenceMarginal>,
}

#[derive(Clone, Debug)]
pub struct WiggleSample {
    pub offset: f64,
    pub lab_age_bp: f64,
    pub lab_sigma: f64,
    pub reservoir_age: f64,
    pub reservoir_sigma: f64,
}

#[derive(Clone, Debug)]
pub struct WiggleCalendarSummary {
    pub sample: usize,
    pub mean_cal_bp: f64,
    pub mode_cal_bp: f64,
}

#[derive(Clone, Debug)]
pub struct WiggleResult {
    pub points: Vec<CalibrationPoint>,
    pub mean_anchor_bp: f64,
    pub mode_anchor_bp: f64,
    pub intervals: Vec<IntervalReport>,
    pub sample_calendar: Vec<WiggleCalendarSummary>,
}

#[derive(Clone, Debug)]
pub struct ReservoirWiggleResult {
    pub joint: Vec<[f64; 3]>,
    pub anchor: PhaseDistribution,
    pub reservoir_shift: PhaseDistribution,
    pub sample_calendar: Vec<WiggleCalendarSummary>,
}

#[derive(Clone, Debug)]
pub struct PhaseSample {
    pub lab_age_bp: f64,
    pub lab_sigma: f64,
    pub reservoir_age: f64,
    pub reservoir_sigma: f64,
}

#[derive(Clone, Debug)]
pub struct PhaseDistribution {
    pub points: Vec<CalibrationPoint>,
    pub mean: f64,
    pub mode: f64,
    pub intervals: Vec<IntervalReport>,
}

#[derive(Clone, Debug)]
pub struct PhaseResult {
    pub boundary_pairs: Vec<[f64; 3]>,
    pub start: PhaseDistribution,
    pub end: PhaseDistribution,
    pub span: PhaseDistribution,
}

pub fn calibrate(input: &CalibrationInput) -> Result<Calibration> {
    if !input.lab_age_bp.is_finite()
        || !input.lab_sigma.is_finite()
        || input.lab_sigma <= 0.0
        || !input.reservoir_age.is_finite()
        || !input.reservoir_sigma.is_finite()
        || input.reservoir_sigma < 0.0
        || !input.start_cal_bp.is_finite()
        || !input.end_cal_bp.is_finite()
        || !input.step.is_finite()
        || input.step <= 0.0
        || input.step.fract() != 0.0
        || input.start_cal_bp > input.end_cal_bp
    {
        return err("invalid calibration input");
    }

    let corrected = input.lab_age_bp - input.reservoir_age;
    let mut log_weights = Vec::new();
    let mut x = input.start_cal_bp;
    while x <= input.end_cal_bp + 1e-12 {
        let c = interpolate(&input.curve, x)?;
        let var = input.lab_sigma * input.lab_sigma
            + c.sigma * c.sigma
            + input.reservoir_sigma * input.reservoir_sigma;
        if var <= 0.0 || !var.is_finite() {
            return err("invalid variance");
        }
        let diff = corrected - c.c14_bp;
        let logw = -0.5 * diff * diff / var - 0.5 * (2.0 * std::f64::consts::PI * var).ln();
        log_weights.push((x, logw));
        x += input.step;
    }
    if log_weights.is_empty() {
        return err("empty calibration grid");
    }

    let max_log = log_weights
        .iter()
        .map(|(_, w)| *w)
        .fold(f64::NEG_INFINITY, f64::max);
    let mut total = 0.0;
    let mut points = Vec::with_capacity(log_weights.len());
    for (cal_bp, logw) in log_weights {
        let w = (logw - max_log).exp();
        if !w.is_finite() {
            return err("invalid calibration weight");
        }
        total += w;
        points.push(CalibrationPoint {
            cal_bp,
            probability: w,
        });
    }
    if total <= 0.0 || !total.is_finite() {
        return err("calibration underflow");
    }

    let mut mean = 0.0;
    let mut mode = points[0].cal_bp;
    let mut best = f64::NEG_INFINITY;
    for p in &mut points {
        p.probability /= total;
        mean += p.cal_bp * p.probability;
        if p.probability >= best {
            best = p.probability;
            mode = p.cal_bp;
        }
    }
    Ok(Calibration {
        points,
        mean_cal_bp: mean,
        mode_cal_bp: mode,
    })
}

pub fn hpd(cal: &Calibration, levels: &[f64], step: f64) -> Result<Vec<IntervalReport>> {
    if cal.points.is_empty() || !step.is_finite() || step <= 0.0 {
        return err("invalid HPD input");
    }
    let mut reports = Vec::with_capacity(levels.len());
    for &level in levels {
        if !level.is_finite() || level <= 0.0 || level > 1.0 {
            return err("invalid HPD level");
        }
        let mut order: Vec<usize> = (0..cal.points.len()).collect();
        order.sort_by(|&a, &b| {
            let pa = cal.points[a].probability;
            let pb = cal.points[b].probability;
            pb.partial_cmp(&pa).unwrap().then_with(|| {
                cal.points[b]
                    .cal_bp
                    .partial_cmp(&cal.points[a].cal_bp)
                    .unwrap()
            })
        });
        let mut selected = vec![false; cal.points.len()];
        let mut mass = 0.0;
        for idx in order {
            if mass >= level {
                break;
            }
            selected[idx] = true;
            mass += cal.points[idx].probability;
        }

        let mut ranges = Vec::new();
        let mut current: Option<[f64; 2]> = None;
        for (idx, p) in cal.points.iter().enumerate() {
            if !selected[idx] {
                continue;
            }
            match current.as_mut() {
                Some(r) if (p.cal_bp - r[1] - step).abs() <= 1e-9 => r[1] = p.cal_bp,
                Some(r) => {
                    ranges.push(*r);
                    current = Some([p.cal_bp, p.cal_bp]);
                }
                None => current = Some([p.cal_bp, p.cal_bp]),
            }
        }
        if let Some(r) = current {
            ranges.push(r);
        }
        reports.push(IntervalReport {
            level,
            ranges,
            mass,
        });
    }
    Ok(reports)
}

pub fn curve_mixture_calibrate(
    models: &[CurveModel],
    lab_age_bp: f64,
    lab_sigma: f64,
    reservoir_age: f64,
    reservoir_sigma: f64,
    start_cal_bp: f64,
    end_cal_bp: f64,
    step: f64,
    levels: &[f64],
) -> Result<CurveMixtureResult> {
    if models.len() < 2 || models.len() > 5 {
        return err("invalid curve model count");
    }
    if !lab_age_bp.is_finite()
        || !lab_sigma.is_finite()
        || lab_sigma <= 0.0
        || !reservoir_age.is_finite()
        || !reservoir_sigma.is_finite()
        || reservoir_sigma < 0.0
        || !start_cal_bp.is_finite()
        || !end_cal_bp.is_finite()
        || !step.is_finite()
        || step <= 0.0
        || step.fract() != 0.0
        || start_cal_bp > end_cal_bp
    {
        return err("invalid curve mixture input");
    }
    for &level in levels {
        if !level.is_finite() || level <= 0.0 || level > 1.0 {
            return err("invalid HPD level");
        }
    }
    for model in models {
        if !model.weight.is_finite() || model.weight <= 0.0 || model.curve.len() < 2 {
            return err("invalid curve model");
        }
    }

    let mut grid = Vec::new();
    let mut x = start_cal_bp;
    while x <= end_cal_bp + 1e-12 {
        grid.push(x);
        x += step;
    }
    if grid.is_empty() {
        return err("empty curve mixture grid");
    }

    let corrected = lab_age_bp - reservoir_age;
    let mut covered = vec![false; grid.len()];
    let mut log_weights = Vec::new();
    for (model_idx, model) in models.iter().enumerate() {
        let log_prior = 0.0;
        for (grid_idx, &cal_bp) in grid.iter().enumerate() {
            let c = match interpolate(&model.curve, cal_bp) {
                Ok(value) => value,
                Err(_) => continue,
            };
            covered[grid_idx] = true;
            let var = lab_sigma * lab_sigma + c.sigma * c.sigma + reservoir_sigma * reservoir_sigma;
            if var <= 0.0 || !var.is_finite() {
                return err("invalid curve mixture variance");
            }
            let diff = corrected - c.c14_bp;
            let logw =
                log_prior - 0.5 * diff * diff / var - 0.5 * (2.0 * std::f64::consts::PI * var).ln();
            log_weights.push((model_idx, grid_idx, logw));
        }
    }
    if covered.iter().any(|&is_covered| !is_covered) {
        return err("curve mixture grid point without model coverage");
    }
    if log_weights.is_empty() {
        return err("no curve mixture weights");
    }

    let max_log = log_weights
        .iter()
        .map(|(_, _, logw)| *logw)
        .fold(f64::NEG_INFINITY, f64::max);
    let mut raw_weights = Vec::with_capacity(log_weights.len());
    let mut total = 0.0;
    for (model_idx, grid_idx, logw) in log_weights {
        let weight = (logw - max_log).exp();
        if !weight.is_finite() {
            return err("invalid curve mixture weight");
        }
        total += weight;
        raw_weights.push((model_idx, grid_idx, weight));
    }
    if total <= 0.0 || !total.is_finite() {
        return err("zero curve mixture posterior");
    }

    let mut joint = Vec::with_capacity(raw_weights.len());
    let mut calendar_probs = vec![0.0; grid.len()];
    let mut curve_probs = vec![0.0; models.len()];
    for (model_idx, grid_idx, weight) in raw_weights {
        let probability = weight / total;
        calendar_probs[grid_idx] += probability;
        curve_probs[model_idx] += probability;
        joint.push([model_idx as f64, grid[grid_idx], probability]);
    }

    let mut points = Vec::with_capacity(grid.len());
    let mut mean = 0.0;
    let mut mode = grid[0];
    let mut best = f64::NEG_INFINITY;
    for (&cal_bp, &probability) in grid.iter().zip(calendar_probs.iter()) {
        mean += cal_bp * probability;
        if probability > best {
            best = probability;
            mode = cal_bp;
        }
        points.push(CalibrationPoint {
            cal_bp,
            probability,
        });
    }
    let calibration = Calibration {
        points: points.clone(),
        mean_cal_bp: mean,
        mode_cal_bp: mode,
    };
    let intervals = hpd(&calibration, levels, step)?;
    let curve_posteriors = curve_probs
        .iter()
        .enumerate()
        .map(|(idx, &probability)| [idx as f64, probability])
        .collect();

    Ok(CurveMixtureResult {
        joint,
        points,
        mean_cal_bp: mean,
        mode_cal_bp: mode,
        curve_posteriors,
        intervals,
    })
}

pub fn combine(dets: &[Determination]) -> Result<Combined> {
    if dets.is_empty() || dets.len() > 11 {
        return err("invalid number of determinations");
    }
    let mut weighted_sum = 0.0;
    let mut weight_sum = 0.0;
    let mut corrected = Vec::with_capacity(dets.len());
    for d in dets {
        if !d.age_bp.is_finite()
            || !d.sigma.is_finite()
            || d.sigma <= 0.0
            || !d.reservoir_age.is_finite()
            || !d.reservoir_sigma.is_finite()
            || d.reservoir_sigma < 0.0
        {
            return err("invalid determination");
        }
        let age = d.age_bp - d.reservoir_age;
        let var = d.sigma * d.sigma + d.reservoir_sigma * d.reservoir_sigma;
        if var <= 0.0 || !var.is_finite() {
            return err("invalid determination variance");
        }
        let weight = 1.0 / var;
        weighted_sum += weight * age;
        weight_sum += weight;
        corrected.push((age, weight));
    }
    if weight_sum <= 0.0 || !weight_sum.is_finite() {
        return err("invalid weights");
    }
    let mean = weighted_sum / weight_sum;
    let sigma = (1.0 / weight_sum).sqrt();
    let chi_square = corrected
        .iter()
        .map(|(age, weight)| weight * (age - mean) * (age - mean))
        .sum::<f64>();
    let dof = dets.len() - 1;
    let passes = dof == 0 || chi_square <= critical_95(dof)?;
    Ok(Combined {
        age_bp: mean,
        sigma,
        chi_square,
        dof,
        passes,
    })
}

pub fn sequence(
    curve: &[CurvePoint],
    samples: &[SequenceSample],
    start_cal_bp: f64,
    end_cal_bp: f64,
    step: f64,
    min_gaps: Option<&[f64]>,
    max_gaps: Option<&[f64]>,
    levels: &[f64],
) -> Result<SequenceResult> {
    if samples.len() < 2 || samples.len() > 6 {
        return err("invalid sequence sample count");
    }
    let n = samples.len();
    if !start_cal_bp.is_finite()
        || !end_cal_bp.is_finite()
        || !step.is_finite()
        || step <= 0.0
        || step.fract() != 0.0
        || start_cal_bp > end_cal_bp
    {
        return err("invalid sequence grid");
    }
    for &level in levels {
        if !level.is_finite() || level <= 0.0 || level > 1.0 {
            return err("invalid HPD level");
        }
    }
    let mut min_bounds = vec![0.0; n - 1];
    if let Some(bounds) = min_gaps {
        if bounds.len() != n - 1 {
            return err("invalid sequence minimum gap count");
        }
        for (idx, &bound) in bounds.iter().enumerate() {
            if !bound.is_finite() || bound < 0.0 {
                return err("invalid sequence minimum gap");
            }
            min_bounds[idx] = bound;
        }
    }
    let mut max_bounds = vec![f64::INFINITY; n - 1];
    if let Some(bounds) = max_gaps {
        if bounds.len() != n - 1 {
            return err("invalid sequence maximum gap count");
        }
        for (idx, &bound) in bounds.iter().enumerate() {
            if !bound.is_finite() || bound < min_bounds[idx] {
                return err("invalid sequence maximum gap");
            }
            max_bounds[idx] = bound;
        }
    }

    let mut independent = Vec::with_capacity(samples.len());
    for sample in samples {
        let cal = calibrate(&CalibrationInput {
            curve: curve.to_vec(),
            lab_age_bp: sample.lab_age_bp,
            lab_sigma: sample.lab_sigma,
            reservoir_age: sample.reservoir_age,
            reservoir_sigma: sample.reservoir_sigma,
            start_cal_bp,
            end_cal_bp,
            step,
        })?;
        independent.push(cal);
    }
    let grid_len = independent[0].points.len();
    if grid_len == 0 || independent.iter().any(|cal| cal.points.len() != grid_len) {
        return err("inconsistent sequence grids");
    }
    let probs: Vec<Vec<f64>> = independent
        .iter()
        .map(|cal| cal.points.iter().map(|p| p.probability).collect())
        .collect();

    let mut left = vec![vec![0.0; grid_len]; n];
    left[0].copy_from_slice(&probs[0]);
    for s in 1..n {
        for j in 0..grid_len {
            let current_bp = independent[s].points[j].cal_bp;
            let mut mass = 0.0;
            for k in 0..grid_len {
                let gap = independent[s - 1].points[k].cal_bp - current_bp;
                if gap + 1e-9 >= min_bounds[s - 1] && gap <= max_bounds[s - 1] + 1e-9 {
                    mass += left[s - 1][k];
                }
            }
            left[s][j] = probs[s][j] * mass;
        }
    }

    let mut right = vec![vec![0.0; grid_len]; n];
    right[n - 1].copy_from_slice(&probs[n - 1]);
    for s in (0..n - 1).rev() {
        for j in 0..grid_len {
            let current_bp = independent[s].points[j].cal_bp;
            let mut mass = 0.0;
            for k in 0..grid_len {
                let gap = current_bp - independent[s + 1].points[k].cal_bp;
                if gap + 1e-9 >= min_bounds[s] && gap <= max_bounds[s] + 1e-9 {
                    mass += right[s + 1][k];
                }
            }
            right[s][j] = probs[s][j] * mass;
        }
    }

    let total: f64 = left[n - 1].iter().sum();
    if total <= 0.0 || !total.is_finite() {
        return err("zero order probability");
    }

    let mut marginals = Vec::with_capacity(n);
    for s in 0..n {
        let mut points = Vec::with_capacity(grid_len);
        let mut mean = 0.0;
        let mut mode = independent[s].points[0].cal_bp;
        let mut best = f64::NEG_INFINITY;
        for j in 0..grid_len {
            let p = if probs[s][j] > 0.0 {
                left[s][j] * right[s][j] / probs[s][j] / total
            } else {
                0.0
            };
            let cal_bp = independent[s].points[j].cal_bp;
            mean += cal_bp * p;
            if p > best {
                best = p;
                mode = cal_bp;
            }
            points.push(CalibrationPoint {
                cal_bp,
                probability: p,
            });
        }
        let calibration = Calibration {
            points,
            mean_cal_bp: mean,
            mode_cal_bp: mode,
        };
        let intervals = hpd(&calibration, levels, step)?;
        marginals.push(SequenceMarginal {
            sample: s,
            calibration,
            intervals,
        });
    }

    Ok(SequenceResult {
        order_probability: total,
        marginals,
    })
}

pub fn wiggle_match(
    curve: &[CurvePoint],
    samples: &[WiggleSample],
    anchor_start_bp: f64,
    anchor_end_bp: f64,
    anchor_step: f64,
    levels: &[f64],
) -> Result<WiggleResult> {
    if samples.len() < 2 || samples.len() > 12 {
        return err("invalid wiggle sample count");
    }
    if !anchor_start_bp.is_finite()
        || !anchor_end_bp.is_finite()
        || !anchor_step.is_finite()
        || anchor_step <= 0.0
        || anchor_step.fract() != 0.0
        || anchor_start_bp > anchor_end_bp
    {
        return err("invalid wiggle anchor grid");
    }
    for &level in levels {
        if !level.is_finite() || level <= 0.0 || level > 1.0 {
            return err("invalid HPD level");
        }
    }

    let mut prev_offset = f64::NEG_INFINITY;
    for (idx, sample) in samples.iter().enumerate() {
        if !sample.offset.is_finite()
            || sample.offset < 0.0
            || sample.offset <= prev_offset
            || !sample.lab_age_bp.is_finite()
            || !sample.lab_sigma.is_finite()
            || sample.lab_sigma <= 0.0
            || !sample.reservoir_age.is_finite()
            || !sample.reservoir_sigma.is_finite()
            || sample.reservoir_sigma < 0.0
        {
            return err("invalid wiggle sample");
        }
        if idx == 0 && sample.offset != 0.0 {
            return err("first wiggle offset must be zero");
        }
        prev_offset = sample.offset;
    }

    let mut log_weights = Vec::new();
    let mut anchor = anchor_start_bp;
    while anchor <= anchor_end_bp + 1e-12 {
        let mut logw = 0.0;
        let mut valid = true;
        for sample in samples {
            let cal_bp = anchor - sample.offset;
            let c = match interpolate(curve, cal_bp) {
                Ok(v) => v,
                Err(_) => {
                    valid = false;
                    break;
                }
            };
            let corrected = sample.lab_age_bp - sample.reservoir_age;
            let var = sample.lab_sigma * sample.lab_sigma
                + c.sigma * c.sigma
                + sample.reservoir_sigma * sample.reservoir_sigma;
            if var <= 0.0 || !var.is_finite() {
                return err("invalid wiggle variance");
            }
            let diff = corrected - c.c14_bp;
            logw += -0.5 * diff * diff / var - 0.5 * (2.0 * std::f64::consts::PI * var).ln();
        }
        if valid {
            log_weights.push((anchor, logw));
        }
        anchor += anchor_step;
    }
    if log_weights.is_empty() {
        return err("no valid wiggle anchors");
    }
    let max_log = log_weights
        .iter()
        .map(|(_, w)| *w)
        .fold(f64::NEG_INFINITY, f64::max);
    let mut total = 0.0;
    let mut points = Vec::with_capacity(log_weights.len());
    for (anchor_bp, logw) in log_weights {
        let w = (logw - max_log).exp();
        if !w.is_finite() {
            return err("invalid wiggle weight");
        }
        total += w;
        points.push(CalibrationPoint {
            cal_bp: anchor_bp,
            probability: w,
        });
    }
    if total <= 0.0 || !total.is_finite() {
        return err("zero wiggle posterior");
    }

    let mut mean = 0.0;
    let mut mode = points[0].cal_bp;
    let mut best = f64::NEG_INFINITY;
    for point in &mut points {
        point.probability /= total;
        mean += point.cal_bp * point.probability;
        if point.probability > best {
            best = point.probability;
            mode = point.cal_bp;
        }
    }
    let anchor_cal = Calibration {
        points: points.clone(),
        mean_cal_bp: mean,
        mode_cal_bp: mode,
    };
    let intervals = hpd(&anchor_cal, levels, anchor_step)?;
    let sample_calendar = samples
        .iter()
        .enumerate()
        .map(|(idx, sample)| WiggleCalendarSummary {
            sample: idx,
            mean_cal_bp: mean + sample.offset,
            mode_cal_bp: mode + sample.offset,
        })
        .collect();

    Ok(WiggleResult {
        points,
        mean_anchor_bp: mean,
        mode_anchor_bp: mode,
        intervals,
        sample_calendar,
    })
}

pub fn reservoir_wiggle_match(
    curve: &[CurvePoint],
    samples: &[WiggleSample],
    anchor_start_bp: f64,
    anchor_end_bp: f64,
    anchor_step: f64,
    shift_start: f64,
    shift_end: f64,
    shift_step: f64,
    levels: &[f64],
) -> Result<ReservoirWiggleResult> {
    if samples.len() < 2 || samples.len() > 12 {
        return err("invalid reservoir wiggle sample count");
    }
    if !anchor_start_bp.is_finite()
        || !anchor_end_bp.is_finite()
        || !anchor_step.is_finite()
        || anchor_step <= 0.0
        || anchor_step.fract() != 0.0
        || anchor_start_bp > anchor_end_bp
        || !shift_start.is_finite()
        || !shift_end.is_finite()
        || !shift_step.is_finite()
        || shift_step <= 0.0
        || shift_step.fract() != 0.0
        || shift_start > shift_end
    {
        return err("invalid reservoir wiggle grid");
    }
    for &level in levels {
        if !level.is_finite() || level <= 0.0 || level > 1.0 {
            return err("invalid HPD level");
        }
    }

    let mut prev_offset = f64::NEG_INFINITY;
    for (idx, sample) in samples.iter().enumerate() {
        if !sample.offset.is_finite()
            || sample.offset < 0.0
            || sample.offset <= prev_offset
            || !sample.lab_age_bp.is_finite()
            || !sample.lab_sigma.is_finite()
            || sample.lab_sigma <= 0.0
            || !sample.reservoir_age.is_finite()
            || !sample.reservoir_sigma.is_finite()
            || sample.reservoir_sigma < 0.0
        {
            return err("invalid reservoir wiggle sample");
        }
        if idx == 0 && sample.offset != 0.0 {
            return err("first reservoir wiggle offset must be zero");
        }
        prev_offset = sample.offset;
    }

    let mut shift_values = Vec::new();
    let mut shift = shift_start;
    while shift <= shift_end + 1e-12 {
        shift_values.push(shift);
        shift += shift_step;
    }
    if shift_values.is_empty() {
        return err("empty reservoir shift grid");
    }

    let mut anchor_values = Vec::new();
    let mut log_weights = Vec::new();
    let mut anchor = anchor_start_bp;
    while anchor <= anchor_end_bp + 1e-12 {
        let mut curve_points = Vec::with_capacity(samples.len());
        let mut valid_anchor = true;
        for sample in samples {
            match interpolate(curve, anchor - sample.offset) {
                Ok(point) => curve_points.push(point),
                Err(_) => {
                    valid_anchor = false;
                    break;
                }
            }
        }
        if valid_anchor {
            let anchor_idx = anchor_values.len();
            anchor_values.push(anchor);
            for (shift_idx, &reservoir_shift) in shift_values.iter().enumerate() {
                let mut logw = 0.0;
                for (sample, c) in samples.iter().zip(curve_points.iter()) {
                    let corrected = sample.lab_age_bp - sample.reservoir_age;
                    let var = sample.lab_sigma * sample.lab_sigma
                        + c.sigma * c.sigma
                        + sample.reservoir_sigma * sample.reservoir_sigma;
                    if var <= 0.0 || !var.is_finite() {
                        return err("invalid reservoir wiggle variance");
                    }
                    let diff = corrected - c.c14_bp;
                    logw +=
                        -0.5 * diff * diff / var - 0.5 * (2.0 * std::f64::consts::PI * var).ln();
                }
                log_weights.push((anchor_idx, shift_idx, logw));
            }
        }
        anchor += anchor_step;
    }
    if log_weights.is_empty() {
        return err("no valid reservoir wiggle pairs");
    }

    let max_log = log_weights
        .iter()
        .map(|(_, _, w)| *w)
        .fold(f64::NEG_INFINITY, f64::max);
    let mut raw_weights = Vec::with_capacity(log_weights.len());
    let mut total = 0.0;
    for (anchor_idx, shift_idx, logw) in log_weights {
        let weight = (logw - max_log).exp();
        if !weight.is_finite() {
            return err("invalid reservoir wiggle weight");
        }
        total += weight;
        raw_weights.push((anchor_idx, shift_idx, weight));
    }
    if total <= 0.0 || !total.is_finite() {
        return err("zero reservoir wiggle posterior");
    }

    let mut joint = Vec::with_capacity(raw_weights.len());
    let mut anchor_probs = vec![0.0; anchor_values.len()];
    let mut shift_probs = vec![0.0; shift_values.len()];
    for (anchor_idx, shift_idx, weight) in raw_weights {
        let probability = weight / total;
        anchor_probs[anchor_idx] += probability;
        shift_probs[shift_idx] += probability;
        joint.push([
            anchor_values[anchor_idx],
            shift_values[shift_idx],
            probability,
        ]);
    }

    let anchor = phase_distribution_from_probs(&anchor_values, &anchor_probs, levels, anchor_step, true)?;
    let reservoir_shift =
        phase_distribution_from_probs(&shift_values, &shift_probs, levels, shift_step, true)?;
    let sample_calendar = samples
        .iter()
        .enumerate()
        .map(|(idx, sample)| WiggleCalendarSummary {
            sample: idx,
            mean_cal_bp: anchor.mean - sample.offset,
            mode_cal_bp: anchor.mode - sample.offset,
        })
        .collect();

    Ok(ReservoirWiggleResult {
        joint,
        anchor,
        reservoir_shift,
        sample_calendar,
    })
}

pub fn phase_bounds(
    curve: &[CurvePoint],
    samples: &[PhaseSample],
    start_cal_bp: f64,
    end_cal_bp: f64,
    step: f64,
    levels: &[f64],
) -> Result<PhaseResult> {
    if samples.len() < 2 || samples.len() > 10 {
        return err("invalid phase sample count");
    }
    if !start_cal_bp.is_finite()
        || !end_cal_bp.is_finite()
        || !step.is_finite()
        || step <= 0.0
        || step.fract() != 0.0
        || start_cal_bp > end_cal_bp
    {
        return err("invalid phase grid");
    }
    for &level in levels {
        if !level.is_finite() || level <= 0.0 || level > 1.0 {
            return err("invalid HPD level");
        }
    }

    let mut calibrated = Vec::with_capacity(samples.len());
    for sample in samples {
        if !sample.lab_age_bp.is_finite()
            || !sample.lab_sigma.is_finite()
            || sample.lab_sigma <= 0.0
            || !sample.reservoir_age.is_finite()
            || !sample.reservoir_sigma.is_finite()
            || sample.reservoir_sigma < 0.0
        {
            return err("invalid phase sample");
        }
        calibrated.push(calibrate(&CalibrationInput {
            curve: curve.to_vec(),
            lab_age_bp: sample.lab_age_bp,
            lab_sigma: sample.lab_sigma,
            reservoir_age: sample.reservoir_age,
            reservoir_sigma: sample.reservoir_sigma,
            start_cal_bp,
            end_cal_bp,
            step,
        })?);
    }

    let grid_len = calibrated[0].points.len();
    if grid_len == 0 || calibrated.iter().any(|cal| cal.points.len() != grid_len) {
        return err("inconsistent phase grids");
    }
    let grid: Vec<f64> = calibrated[0].points.iter().map(|p| p.cal_bp).collect();
    let mut prefixes = Vec::with_capacity(calibrated.len());
    for cal in &calibrated {
        let mut prefix = Vec::with_capacity(grid_len + 1);
        prefix.push(0.0);
        for p in &cal.points {
            prefix.push(prefix.last().unwrap() + p.probability);
        }
        prefixes.push(prefix);
    }

    let mut raw_pairs = Vec::new();
    let mut total = 0.0;
    for start_idx in 0..grid_len {
        for end_idx in 0..=start_idx {
            let mut weight = 1.0;
            for prefix in &prefixes {
                let mass = prefix[start_idx + 1] - prefix[end_idx];
                weight *= mass.max(0.0);
            }
            if weight.is_finite() && weight > 0.0 {
                total += weight;
                raw_pairs.push((start_idx, end_idx, weight));
            }
        }
    }
    if total <= 0.0 || !total.is_finite() {
        return err("zero phase posterior");
    }

    let mut boundary_pairs = Vec::with_capacity(raw_pairs.len());
    let mut start_probs = vec![0.0; grid_len];
    let mut end_probs = vec![0.0; grid_len];
    let mut span_probs = vec![0.0; grid_len];
    for (start_idx, end_idx, weight) in raw_pairs {
        let prob = weight / total;
        start_probs[start_idx] += prob;
        end_probs[end_idx] += prob;
        span_probs[start_idx - end_idx] += prob;
        boundary_pairs.push([grid[start_idx], grid[end_idx], prob]);
    }

    let start = phase_distribution_from_probs(&grid, &start_probs, levels, step, false)?;
    let end = phase_distribution_from_probs(&grid, &end_probs, levels, step, false)?;
    let span_grid: Vec<f64> = (0..grid_len).map(|i| i as f64 * step).collect();
    let span = phase_distribution_from_probs(&span_grid, &span_probs, levels, step, false)?;

    Ok(PhaseResult {
        boundary_pairs,
        start,
        end,
        span,
    })
}

fn phase_distribution_from_probs(
    values: &[f64],
    probs: &[f64],
    levels: &[f64],
    step: f64,
    keep_zero_points: bool,
) -> Result<PhaseDistribution> {
    let mut points = Vec::new();
    for (&value, &prob) in values.iter().zip(probs.iter()) {
        if keep_zero_points || prob > 0.0 {
            points.push(CalibrationPoint {
                cal_bp: value,
                probability: prob,
            });
        }
    }
    if points.is_empty() {
        return err("empty phase distribution");
    }
    let mut mean = 0.0;
    let mut mode = points[0].cal_bp;
    let mut best = f64::NEG_INFINITY;
    for p in &points {
        mean += p.cal_bp * p.probability;
        if p.probability > best {
            best = p.probability;
            mode = p.cal_bp;
        }
    }
    let cal = Calibration {
        points: points.clone(),
        mean_cal_bp: mean,
        mode_cal_bp: mode,
    };
    let intervals = hpd(&cal, levels, step)?;
    Ok(PhaseDistribution {
        points,
        mean,
        mode,
        intervals,
    })
}

fn critical_95(dof: usize) -> Result<f64> {
    match dof {
        1 => Ok(3.841458820694124),
        2 => Ok(5.991464547107979),
        3 => Ok(7.814727903251179),
        4 => Ok(9.487729036781154),
        5 => Ok(11.070497693516351),
        6 => Ok(12.591587243743977),
        7 => Ok(14.067140449340169),
        8 => Ok(15.50731305586545),
        9 => Ok(16.918977604620448),
        10 => Ok(18.307038053275146),
        _ => err("unsupported degrees of freedom"),
    }
}
