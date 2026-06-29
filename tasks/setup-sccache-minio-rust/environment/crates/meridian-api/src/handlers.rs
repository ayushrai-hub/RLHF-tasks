use crate::routes::{RouteTable, RouteTarget};
use meridian_core::Pipeline;
use meridian_proto::{decode_record, EventRecord};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum HandlerError {
    #[error(transparent)]
    Codec(#[from] meridian_proto::CodecError),
    #[error("route {0:?} rejected payload")]
    Rejected(RouteTarget),
    #[error(transparent)]
    Pipeline(#[from] meridian_core::PipelineError),
}

pub fn handle_event(bytes: &[u8]) -> Result<String, HandlerError> {
    let record: EventRecord = decode_record(bytes)?;
    let target = RouteTable::resolve(&record);
    match target {
        RouteTarget::Discard => Err(HandlerError::Rejected(target)),
        RouteTarget::Archive | RouteTarget::Ingest => {
            let pipeline = Pipeline::default();
            Ok(pipeline.run(record.payload.as_bytes())?)
        }
    }
}
