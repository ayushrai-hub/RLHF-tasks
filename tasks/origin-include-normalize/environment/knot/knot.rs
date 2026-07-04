use crate::errors::Err;
use crate::model::{Root, Row};

pub fn cast_e(root: &mut Root, rows: &[Row]) -> Result<(), Err> {
    let path = root.state_dir().join("material.bin");
    let mut buf = Vec::new();
    buf.extend_from_slice(b"ZNMT");
    buf.push(1u8);
    let count = rows.len() as u16;
    buf.extend_from_slice(&count.to_le_bytes());
    let mut keyed: Vec<&Row> = rows.iter().collect();
    keyed.sort_by_key(|row| row.key.as_str());
    for row in keyed {
        let id = row.key.as_bytes();
        buf.push(id.len() as u8);
        buf.extend_from_slice(id);
        buf.extend_from_slice(&row.byte.to_le_bytes());
        buf.extend_from_slice(&row.pkt.to_le_bytes());
        let body = row.body.as_bytes();
        buf.push(body.len() as u8);
        buf.extend_from_slice(body);
    }
    crate::io::write_blob(&path, &buf)?;
    Ok(())
}
