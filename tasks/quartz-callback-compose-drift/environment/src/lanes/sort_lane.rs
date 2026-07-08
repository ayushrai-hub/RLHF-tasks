use crate::qz::n1::q1::sort_callbacks;
use crate::qz::n6::q6::tiebreak_index;
use crate::types::CallbackSpec;

pub fn sorted_indices(callbacks: &[CallbackSpec]) -> Vec<usize> {
    let mut keyed: Vec<(usize, usize, usize)> = callbacks
        .iter()
        .enumerate()
        .map(|(i, cb)| {
            (
                tiebreak_index(cb.registration),
                cb.load_order as usize,
                i,
            )
        })
        .collect();
    sort_callbacks(&mut keyed);
    keyed.iter().map(|(_, _, i)| *i).collect()
}
