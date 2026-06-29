use crate::hash::digest_hex;
use thiserror::Error;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Stage {
    Ingest,
    Transform,
    Emit,
}

#[derive(Debug, Error)]
pub enum PipelineError {
    #[error("stage {0:?} rejected payload")]
    Rejected(Stage),
    #[error(transparent)]
    Digest(#[from] crate::hash::DigestError),
}

pub struct Pipeline {
    stages: Vec<Stage>,
}

impl Default for Pipeline {
    fn default() -> Self {
        Self {
            stages: vec![Stage::Ingest, Stage::Transform, Stage::Emit],
        }
    }
}

impl Pipeline {
    pub fn new(stages: Vec<Stage>) -> Self {
        Self { stages }
    }

    pub fn run(&self, payload: &[u8]) -> Result<String, PipelineError> {
        if payload.is_empty() {
            return Err(PipelineError::Rejected(Stage::Ingest));
        }
        let mut current = payload.to_vec();
        for stage in &self.stages {
            current = match stage {
                Stage::Ingest => current,
                Stage::Transform => {
                    let mut rotated = current.clone();
                    if let Some(first) = rotated.first().copied() {
                        rotated.remove(0);
                        rotated.push(first);
                    }
                    rotated
                }
                Stage::Emit => current,
            };
        }
        Ok(digest_hex(&current)?)
    }
}
