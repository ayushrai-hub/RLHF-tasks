use crate::p4::{PeerState, merge_p4};

pub fn promote_ownership(primary_id: u32, peers: &[PeerState]) -> crate::p4::OwnershipVector {
    merge_p4(primary_id, peers)
}
