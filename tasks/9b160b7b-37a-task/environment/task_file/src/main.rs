use std::process::ExitCode;

use radiocal::calibrate::{
    calibrate, combine, curve_mixture_calibrate, hpd, phase_bounds, reservoir_wiggle_match,
    sequence, wiggle_match, Calibration, CalibrationInput, Combined, CurveMixtureResult,
    CurveModel, Determination, IntervalReport, PhaseDistribution, PhaseResult, PhaseSample,
    ReservoirWiggleResult, SequenceMarginal, SequenceResult, SequenceSample,
    WiggleCalendarSummary, WiggleResult, WiggleSample,
};
use radiocal::curve::{interpolate, parse_curve};
use radiocal::error::{Error, Result};
use radiocal::json::{self, Json};

fn field<'a>(obj: &'a Json, key: &str) -> Result<&'a Json> {
    obj.get(key)
        .ok_or_else(|| Error(format!("missing field {:?}", key)))
}

fn num_field(obj: &Json, key: &str) -> Result<f64> {
    field(obj, key)?
        .as_f64()
        .ok_or_else(|| Error(format!("field {:?} must be a number", key)))
}

fn str_field<'a>(obj: &'a Json, key: &str) -> Result<&'a str> {
    field(obj, key)?
        .as_str()
        .ok_or_else(|| Error(format!("field {:?} must be a string", key)))
}

fn levels_field(obj: &Json) -> Result<Vec<f64>> {
    let rows = field(obj, "levels")?
        .as_array()
        .ok_or_else(|| Error("levels must be an array".to_string()))?;
    let mut levels = Vec::with_capacity(rows.len());
    for row in rows {
        levels.push(
            row.as_f64()
                .ok_or_else(|| Error("levels must contain numbers".to_string()))?,
        );
    }
    Ok(levels)
}

fn optional_number_array_field(obj: &Json, key: &str) -> Result<Option<Vec<f64>>> {
    let Some(value) = obj.get(key) else {
        return Ok(None);
    };
    let rows = value
        .as_array()
        .ok_or_else(|| Error(format!("field {:?} must be an array", key)))?;
    let mut nums = Vec::with_capacity(rows.len());
    for row in rows {
        nums.push(
            row.as_f64()
                .ok_or_else(|| Error(format!("field {:?} must contain numbers", key)))?,
        );
    }
    Ok(Some(nums))
}

fn calibration_input(op: &Json) -> Result<CalibrationInput> {
    Ok(CalibrationInput {
        curve: parse_curve(field(op, "curve")?)?,
        lab_age_bp: num_field(op, "lab_age_bp")?,
        lab_sigma: num_field(op, "lab_sigma")?,
        reservoir_age: num_field(op, "reservoir_age")?,
        reservoir_sigma: num_field(op, "reservoir_sigma")?,
        start_cal_bp: num_field(op, "start_cal_bp")?,
        end_cal_bp: num_field(op, "end_cal_bp")?,
        step: num_field(op, "step")?,
    })
}

fn determinations_field(op: &Json) -> Result<Vec<Determination>> {
    let rows = field(op, "determinations")?
        .as_array()
        .ok_or_else(|| Error("determinations must be an array".to_string()))?;
    let mut dets = Vec::with_capacity(rows.len());
    for row in rows {
        dets.push(Determination {
            age_bp: num_field(row, "age_bp")?,
            sigma: num_field(row, "sigma")?,
            reservoir_age: num_field(row, "reservoir_age")?,
            reservoir_sigma: num_field(row, "reservoir_sigma")?,
        });
    }
    Ok(dets)
}

fn curve_models_field(op: &Json) -> Result<Vec<CurveModel>> {
    let rows = field(op, "curves")?
        .as_array()
        .ok_or_else(|| Error("curves must be an array".to_string()))?;
    let mut models = Vec::with_capacity(rows.len());
    for row in rows {
        models.push(CurveModel {
            weight: num_field(row, "weight")?,
            curve: parse_curve(field(row, "curve")?)?,
        });
    }
    Ok(models)
}

fn sequence_samples_field(op: &Json) -> Result<Vec<SequenceSample>> {
    let rows = field(op, "samples")?
        .as_array()
        .ok_or_else(|| Error("samples must be an array".to_string()))?;
    let mut samples = Vec::with_capacity(rows.len());
    for row in rows {
        samples.push(SequenceSample {
            lab_age_bp: num_field(row, "lab_age_bp")?,
            lab_sigma: num_field(row, "lab_sigma")?,
            reservoir_age: num_field(row, "reservoir_age")?,
            reservoir_sigma: num_field(row, "reservoir_sigma")?,
        });
    }
    Ok(samples)
}

fn wiggle_samples_field(op: &Json) -> Result<Vec<WiggleSample>> {
    let rows = field(op, "samples")?
        .as_array()
        .ok_or_else(|| Error("samples must be an array".to_string()))?;
    let mut samples = Vec::with_capacity(rows.len());
    for row in rows {
        samples.push(WiggleSample {
            offset: num_field(row, "offset")?,
            lab_age_bp: num_field(row, "lab_age_bp")?,
            lab_sigma: num_field(row, "lab_sigma")?,
            reservoir_age: num_field(row, "reservoir_age")?,
            reservoir_sigma: num_field(row, "reservoir_sigma")?,
        });
    }
    Ok(samples)
}

fn phase_samples_field(op: &Json) -> Result<Vec<PhaseSample>> {
    let rows = field(op, "samples")?
        .as_array()
        .ok_or_else(|| Error("samples must be an array".to_string()))?;
    let mut samples = Vec::with_capacity(rows.len());
    for row in rows {
        samples.push(PhaseSample {
            lab_age_bp: num_field(row, "lab_age_bp")?,
            lab_sigma: num_field(row, "lab_sigma")?,
            reservoir_age: num_field(row, "reservoir_age")?,
            reservoir_sigma: num_field(row, "reservoir_sigma")?,
        });
    }
    Ok(samples)
}

fn curve_point_json(p: radiocal::curve::CurvePoint) -> Json {
    Json::Obj(vec![
        ("c14_bp".to_string(), Json::Num(p.c14_bp)),
        ("sigma".to_string(), Json::Num(p.sigma)),
    ])
}

fn pair_json(a: f64, b: f64) -> Json {
    Json::Arr(vec![Json::Num(a), Json::Num(b)])
}

fn points_json(cal: &Calibration) -> Json {
    Json::Arr(
        cal.points
            .iter()
            .map(|p| pair_json(p.cal_bp, p.probability))
            .collect(),
    )
}

fn calibration_json(cal: &Calibration) -> Json {
    Json::Obj(vec![
        ("points".to_string(), points_json(cal)),
        ("mean_cal_bp".to_string(), Json::Num(cal.mean_cal_bp)),
        ("mode_cal_bp".to_string(), Json::Num(cal.mode_cal_bp)),
    ])
}

fn interval_json(report: &IntervalReport) -> Json {
    Json::Obj(vec![
        ("level".to_string(), Json::Num(report.level)),
        (
            "ranges".to_string(),
            Json::Arr(
                report
                    .ranges
                    .iter()
                    .map(|r| pair_json(r[0], r[1]))
                    .collect(),
            ),
        ),
        ("mass".to_string(), Json::Num(report.mass)),
    ])
}

fn hpd_json(cal: &Calibration, reports: &[IntervalReport]) -> Json {
    Json::Obj(vec![
        ("points".to_string(), points_json(cal)),
        ("mean_cal_bp".to_string(), Json::Num(cal.mean_cal_bp)),
        ("mode_cal_bp".to_string(), Json::Num(cal.mode_cal_bp)),
        (
            "intervals".to_string(),
            Json::Arr(reports.iter().map(interval_json).collect()),
        ),
    ])
}

fn curve_mixture_json(result: &CurveMixtureResult) -> Json {
    let cal = Calibration {
        points: result.points.clone(),
        mean_cal_bp: result.mean_cal_bp,
        mode_cal_bp: result.mode_cal_bp,
    };
    Json::Obj(vec![
        ("joint".to_string(), triples_json(&result.joint)),
        ("points".to_string(), points_json(&cal)),
        ("mean_cal_bp".to_string(), Json::Num(result.mean_cal_bp)),
        ("mode_cal_bp".to_string(), Json::Num(result.mode_cal_bp)),
        (
            "curve_posteriors".to_string(),
            Json::Arr(
                result
                    .curve_posteriors
                    .iter()
                    .map(|row| pair_json(row[0], row[1]))
                    .collect(),
            ),
        ),
        (
            "intervals".to_string(),
            Json::Arr(result.intervals.iter().map(interval_json).collect()),
        ),
    ])
}

fn combined_json(c: &Combined) -> Json {
    Json::Obj(vec![
        ("age_bp".to_string(), Json::Num(c.age_bp)),
        ("sigma".to_string(), Json::Num(c.sigma)),
        ("chi_square".to_string(), Json::Num(c.chi_square)),
        ("dof".to_string(), Json::Num(c.dof as f64)),
        ("passes".to_string(), Json::Bool(c.passes)),
    ])
}

fn marginal_json(m: &SequenceMarginal) -> Json {
    Json::Obj(vec![
        ("sample".to_string(), Json::Num(m.sample as f64)),
        ("points".to_string(), points_json(&m.calibration)),
        (
            "mean_cal_bp".to_string(),
            Json::Num(m.calibration.mean_cal_bp),
        ),
        (
            "mode_cal_bp".to_string(),
            Json::Num(m.calibration.mode_cal_bp),
        ),
        (
            "intervals".to_string(),
            Json::Arr(m.intervals.iter().map(interval_json).collect()),
        ),
    ])
}

fn sequence_json(result: &SequenceResult) -> Json {
    Json::Obj(vec![
        (
            "order_probability".to_string(),
            Json::Num(result.order_probability),
        ),
        (
            "marginals".to_string(),
            Json::Arr(result.marginals.iter().map(marginal_json).collect()),
        ),
    ])
}

fn wiggle_calendar_json(summary: &WiggleCalendarSummary) -> Json {
    Json::Obj(vec![
        ("sample".to_string(), Json::Num(summary.sample as f64)),
        ("mean_cal_bp".to_string(), Json::Num(summary.mean_cal_bp)),
        ("mode_cal_bp".to_string(), Json::Num(summary.mode_cal_bp)),
    ])
}

fn wiggle_json(result: &WiggleResult) -> Json {
    let cal = Calibration {
        points: result.points.clone(),
        mean_cal_bp: result.mean_anchor_bp,
        mode_cal_bp: result.mode_anchor_bp,
    };
    Json::Obj(vec![
        ("points".to_string(), points_json(&cal)),
        (
            "mean_anchor_bp".to_string(),
            Json::Num(result.mean_anchor_bp),
        ),
        (
            "mode_anchor_bp".to_string(),
            Json::Num(result.mode_anchor_bp),
        ),
        (
            "intervals".to_string(),
            Json::Arr(result.intervals.iter().map(interval_json).collect()),
        ),
        (
            "sample_calendar".to_string(),
            Json::Arr(
                result
                    .sample_calendar
                    .iter()
                    .map(wiggle_calendar_json)
                    .collect(),
            ),
        ),
    ])
}

fn reservoir_wiggle_json(result: &ReservoirWiggleResult) -> Json {
    Json::Obj(vec![
        ("joint".to_string(), triples_json(&result.joint)),
        (
            "anchor".to_string(),
            phase_distribution_json(&result.anchor, "mean_anchor_bp", "mode_anchor_bp"),
        ),
        (
            "reservoir_shift".to_string(),
            phase_distribution_json(&result.reservoir_shift, "mean_years", "mode_years"),
        ),
        (
            "sample_calendar".to_string(),
            Json::Arr(
                result
                    .sample_calendar
                    .iter()
                    .map(wiggle_calendar_json)
                    .collect(),
            ),
        ),
    ])
}

fn triples_json(rows: &[[f64; 3]]) -> Json {
    Json::Arr(
        rows.iter()
            .map(|r| Json::Arr(vec![Json::Num(r[0]), Json::Num(r[1]), Json::Num(r[2])]))
            .collect(),
    )
}

fn phase_distribution_json(dist: &PhaseDistribution, mean_key: &str, mode_key: &str) -> Json {
    let cal = Calibration {
        points: dist.points.clone(),
        mean_cal_bp: dist.mean,
        mode_cal_bp: dist.mode,
    };
    Json::Obj(vec![
        ("points".to_string(), points_json(&cal)),
        (mean_key.to_string(), Json::Num(dist.mean)),
        (mode_key.to_string(), Json::Num(dist.mode)),
        (
            "intervals".to_string(),
            Json::Arr(dist.intervals.iter().map(interval_json).collect()),
        ),
    ])
}

fn phase_json(result: &PhaseResult) -> Json {
    Json::Obj(vec![
        (
            "boundary_pairs".to_string(),
            triples_json(&result.boundary_pairs),
        ),
        (
            "start".to_string(),
            phase_distribution_json(&result.start, "mean_cal_bp", "mode_cal_bp"),
        ),
        (
            "end".to_string(),
            phase_distribution_json(&result.end, "mean_cal_bp", "mode_cal_bp"),
        ),
        (
            "span".to_string(),
            phase_distribution_json(&result.span, "mean_years", "mode_years"),
        ),
    ])
}

fn run_op(op: &Json) -> Result<Json> {
    match str_field(op, "kind")? {
        "interpolate" => {
            let curve = parse_curve(field(op, "curve")?)?;
            Ok(curve_point_json(interpolate(
                &curve,
                num_field(op, "cal_bp")?,
            )?))
        }
        "calibrate" => Ok(calibration_json(&calibrate(&calibration_input(op)?)?)),
        "hpd" => {
            let input = calibration_input(op)?;
            let levels = levels_field(op)?;
            let cal = calibrate(&input)?;
            let reports = hpd(&cal, &levels, input.step)?;
            Ok(hpd_json(&cal, &reports))
        }
        "curve_mixture_calibrate" => {
            let models = curve_models_field(op)?;
            let levels = levels_field(op)?;
            Ok(curve_mixture_json(&curve_mixture_calibrate(
                &models,
                num_field(op, "lab_age_bp")?,
                num_field(op, "lab_sigma")?,
                num_field(op, "reservoir_age")?,
                num_field(op, "reservoir_sigma")?,
                num_field(op, "start_cal_bp")?,
                num_field(op, "end_cal_bp")?,
                num_field(op, "step")?,
                &levels,
            )?))
        }
        "combine" => Ok(combined_json(&combine(&determinations_field(op)?)?)),
        "sequence" => {
            let curve = parse_curve(field(op, "curve")?)?;
            let samples = sequence_samples_field(op)?;
            let min_gaps = optional_number_array_field(op, "min_gaps")?;
            let max_gaps = optional_number_array_field(op, "max_gaps")?;
            let levels = levels_field(op)?;
            Ok(sequence_json(&sequence(
                &curve,
                &samples,
                num_field(op, "start_cal_bp")?,
                num_field(op, "end_cal_bp")?,
                num_field(op, "step")?,
                min_gaps.as_deref(),
                max_gaps.as_deref(),
                &levels,
            )?))
        }
        "wiggle_match" => {
            let curve = parse_curve(field(op, "curve")?)?;
            let samples = wiggle_samples_field(op)?;
            let levels = levels_field(op)?;
            Ok(wiggle_json(&wiggle_match(
                &curve,
                &samples,
                num_field(op, "anchor_start_bp")?,
                num_field(op, "anchor_end_bp")?,
                num_field(op, "anchor_step")?,
                &levels,
            )?))
        }
        "reservoir_wiggle_match" => {
            let curve = parse_curve(field(op, "curve")?)?;
            let samples = wiggle_samples_field(op)?;
            let levels = levels_field(op)?;
            Ok(reservoir_wiggle_json(&reservoir_wiggle_match(
                &curve,
                &samples,
                num_field(op, "anchor_start_bp")?,
                num_field(op, "anchor_end_bp")?,
                num_field(op, "anchor_step")?,
                num_field(op, "shift_start")?,
                num_field(op, "shift_end")?,
                num_field(op, "shift_step")?,
                &levels,
            )?))
        }
        "phase_bounds" => {
            let curve = parse_curve(field(op, "curve")?)?;
            let samples = phase_samples_field(op)?;
            let levels = levels_field(op)?;
            Ok(phase_json(&phase_bounds(
                &curve,
                &samples,
                num_field(op, "start_cal_bp")?,
                num_field(op, "end_cal_bp")?,
                num_field(op, "step")?,
                &levels,
            )?))
        }
        other => Err(Error(format!("unknown operation {:?}", other))),
    }
}

fn result_obj(kind: String, output: Json, error: bool) -> Json {
    Json::Obj(vec![
        ("kind".to_string(), Json::Str(kind)),
        ("output".to_string(), output),
        ("error".to_string(), Json::Bool(error)),
    ])
}

fn run() -> Result<String> {
    let path = std::env::args()
        .nth(1)
        .ok_or_else(|| Error("usage: radiocal <cases.json>".to_string()))?;
    let text = std::fs::read_to_string(&path)
        .map_err(|e| Error(format!("cannot read {}: {}", path, e)))?;
    let doc = json::parse(&text)?;
    let cases = doc
        .as_array()
        .ok_or_else(|| Error("top-level JSON must be an array".to_string()))?;
    let mut out_cases = Vec::with_capacity(cases.len());
    for case in cases {
        let id = str_field(case, "id")?;
        let ops = field(case, "ops")?
            .as_array()
            .ok_or_else(|| Error("case ops must be an array".to_string()))?;
        let mut results = Vec::with_capacity(ops.len());
        for op in ops {
            let kind = op
                .get("kind")
                .and_then(Json::as_str)
                .unwrap_or("")
                .to_string();
            match run_op(op) {
                Ok(output) => results.push(result_obj(kind, output, false)),
                Err(_) => results.push(result_obj(kind, Json::Null, true)),
            }
        }
        out_cases.push(Json::Obj(vec![
            ("id".to_string(), Json::Str(id.to_string())),
            ("results".to_string(), Json::Arr(results)),
        ]));
    }
    Ok(json::stringify(&Json::Arr(out_cases)))
}

fn main() -> ExitCode {
    match run() {
        Ok(out) => {
            println!("{}", out);
            ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("{}", e);
            ExitCode::from(1)
        }
    }
}
