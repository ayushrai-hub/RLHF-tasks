use meridian_proto::{EventRecord, RecordKind};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RouteTarget {
    Ingest,
    Archive,
    Discard,
}

pub struct RouteTable;

impl RouteTable {
    pub fn resolve(record: &EventRecord) -> RouteTarget {
        match record.kind {
            RecordKind::Heartbeat => RouteTarget::Discard,
            RecordKind::Snapshot => RouteTarget::Archive,
            RecordKind::Delta => RouteTarget::Ingest,
        }
    }
}
