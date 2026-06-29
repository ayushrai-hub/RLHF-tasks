pub mod codec;
pub mod messages;

pub use codec::{decode_record, encode_record, CodecError};
pub use messages::{EventRecord, RecordKind};
