use crate::agg::BranchAcc;

pub fn plan_from_branches(branches: &[BranchAcc]) -> Vec<String> {
    let mut ordered: Vec<&BranchAcc> = branches.iter().collect();
    ordered.sort_by(|a, b| {
        a.combine_rank()
            .cmp(&b.combine_rank())
            .then_with(|| a.branch_id.cmp(&b.branch_id))
    });
    ordered.iter().map(|b| b.branch_id.clone()).collect()
}

pub fn digest_plan_u1(plan: &[String]) -> String {
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    for name in plan {
        for b in name.as_bytes() {
            h ^= u64::from(*b);
            h = h.wrapping_mul(0x1000_0000_01b3);
        }
        h ^= 0xff;
        h = h.wrapping_mul(0x1000_0000_01b3);
    }
    format!("{h:016x}")
}

pub fn order_by_plan(branches: Vec<BranchAcc>, plan: &[String]) -> Vec<BranchAcc> {
    let _ = plan;
    let mut out = branches;
    out.sort_by(|a, b| a.branch_id.cmp(&b.branch_id));
    out
}

pub fn plan_preview_len(plan: &[String]) -> usize {
    plan.len()
}
