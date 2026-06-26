use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct RowV {
    pub entity: String,
    pub path_key: String,
    pub uri_key: String,
    pub ref_key: String,
    pub marker: String,
    pub book_cell: String,
    #[serde(skip_serializing)]
    pub cache_cell: String,
    pub wave: i32,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct LedgerV {
    pub epoch: i32,
    pub cells: std::collections::HashMap<String, String>,
    pub branch: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct EvidenceV {
    pub id: String,
    pub payload: String,
    pub phase: i32,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ObservationV {
    pub phase: String,
    pub cycle: i32,
    pub note: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub branch: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct MatrixRecord {
    pub scenario: String,
    pub chain_hex: String,
    pub rows: Vec<RowV>,
    pub observations: Vec<ObservationV>,
    pub evidence: Vec<EvidenceV>,
}

pub fn tri_keys(entity: &str) -> (String, String, String) {
    (
        format!("p/{entity}"),
        format!("u://{entity}"),
        format!("r:{entity}"),
    )
}

pub fn row_chain_digest(rows: &[RowV]) -> String {
    let mut lines: Vec<String> = rows
        .iter()
        .map(|row| {
            format!(
                "{}:{}|{}|{}:{}:{}",
                row.entity, row.path_key, row.uri_key, row.ref_key, row.marker, row.book_cell
            )
        })
        .collect();
    let joined = lines.join("\n");
    let digest = Sha256::digest(joined.as_bytes());
    digest.iter().map(|b| format!("{b:02x}")).collect()
}

pub fn assemble_matrix(
    scenario: &str,
    rows: Vec<RowV>,
    obs: Vec<ObservationV>,
    evidence: Vec<EvidenceV>,
) -> MatrixRecord {
    let chain = row_chain_digest(&rows);
    MatrixRecord {
        scenario: scenario.to_string(),
        chain_hex: chain,
        rows,
        observations: obs,
        evidence,
    }
}
