use serde_json::Value;

use crate::ingest::pipeline::MemoryRecord;

pub fn build_retrieval_index(_records: &[MemoryRecord]) -> Value {
    Value::Null
}
