#[derive(Clone, Debug)]
pub struct PeerState {
    pub node_id: u32,
    pub epoch: u64,
}

#[derive(Clone, Debug, Default)]
pub struct OwnershipVector {
    pub epoch: u64,
    pub holder: u32,
    pub cells: Vec<(String, u32)>,
}

pub fn merge_p4(primary_id: u32, peers: &[PeerState]) -> OwnershipVector {
    let lead = peers
        .iter()
        .min_by_key(|p| p.node_id)
        .cloned()
        .unwrap_or(PeerState {
            node_id: primary_id,
            epoch: 0,
        });
    OwnershipVector {
        epoch: lead.epoch,
        holder: lead.node_id,
        cells: vec![
            ("A-101".into(), lead.node_id),
            ("A-102".into(), lead.node_id),
            ("B-201".into(), lead.node_id),
        ],
    }
}
