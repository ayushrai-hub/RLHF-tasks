use crate::sx::n2::x2::bundle_digest;
use crate::types::CaseOut;
use serde::Serialize;
use std::fs;
use std::io::Write;
use std::path::Path;

#[derive(Serialize)]
struct Bundle {
    schema_version: String,
    cases: Vec<CaseOut>,
    digest: String,
}

fn bool_lower(v: bool) -> &'static str {
    if v {
        "True"
    } else {
        "False"
    }
}

pub fn write_outputs(cases: &[CaseOut], out_dir: &Path) -> std::io::Result<()> {
    fs::create_dir_all(out_dir)?;
    let digest_rows: Vec<(String, i32, f64)> = cases
        .iter()
        .map(|c| (c.tag.clone(), c.event_step, c.metric_integral))
        .collect();
    let digest = bundle_digest(&digest_rows);
    let bundle = Bundle {
        schema_version: "run.v1".into(),
        cases: cases.to_vec(),
        digest,
    };
    fs::write(
        out_dir.join("run_summary.json"),
        serde_json::to_string_pretty(&bundle).unwrap(),
    )?;
    let mut csv = fs::File::create(out_dir.join("trace.csv"))?;
    writeln!(
        csv,
        "tag,event_step,metric_integral,order_sensitive,euler_ok,event_ok,restart_ok,metric_ok,summary_ok,report_line"
    )?;
    for c in cases {
        writeln!(
            csv,
            "{},{},{},{},{},{},{},{},{},{}",
            c.tag,
            c.event_step,
            c.metric_integral,
            bool_lower(c.order_sensitive),
            bool_lower(c.euler_ok),
            bool_lower(c.event_ok),
            bool_lower(c.restart_ok),
            bool_lower(c.metric_ok),
            bool_lower(c.summary_ok),
            c.report_line
        )?;
    }
    Ok(())
}
