use std::collections::BTreeMap;

use crate::sim::batch::Leg;
use crate::sim::ledger::Ledger;

#[derive(Clone, Debug)]
pub struct Scenario {
    pub name: &'static str,
    pub steps: u32,
    pub save_at: u32,
    pub checkpoint_leg: u32,
    pub resume_from: u32,
    pub compact_at: u32,
    pub pots: BTreeMap<u32, i64>,
    pub batches: Vec<Vec<Leg>>,
}

impl Scenario {
    pub fn initial_state(&self) -> Ledger {
        Ledger::new(self.pots.clone())
    }

    pub fn batch_at(&self, step: u32) -> &[Leg] {
        &self.batches[step as usize % self.batches.len()]
    }
}

pub fn bundled_scenario_names() -> &'static [&'static str] {
    &[
        "copper_wire_fan",
        "nickel_merge_lane",
        "slate_purge_arc",
        "brass_split_ladder",
        "iron_cross_weave",
        "mercury_gate_fold",
    ]
}

pub fn probe_scenario_names() -> &'static [&'static str] {
    &["quartz_ledger_skew", "obsidian_tail_fold"]
}

pub fn cases() -> Vec<Scenario> {
    let mut out = bundled_scenarios();
    out.extend(probe_scenarios());
    out
}

pub fn bundled_scenarios() -> Vec<Scenario> {
    vec![
        Scenario {
            name: "copper_wire_fan",
            steps: 14,
            save_at: 4,
            checkpoint_leg: 1,
            resume_from: 9,
            compact_at: 10,
            pots: BTreeMap::from([(11, 120), (19, 80)]),
            batches: vec![
                vec![
                    Leg::Open(31, 50),
                    Leg::Move(11, 31, 20),
                    Leg::Move(19, 31, 10),
                    Leg::Close,
                ],
                vec![Leg::Move(31, 11, 5), Leg::Close],
                vec![Leg::Open(44, 30), Leg::Move(31, 44, 15), Leg::Close],
                vec![Leg::Move(44, 19, 8), Leg::Close],
                vec![
                    Leg::Move(11, 44, 12),
                    Leg::Move(19, 31, 6),
                    Leg::Close,
                ],
                vec![Leg::Retire(31), Leg::Move(44, 11, 4), Leg::Close],
                vec![Leg::Open(52, 25), Leg::Move(11, 52, 10), Leg::Close],
            ],
        },
        Scenario {
            name: "nickel_merge_lane",
            steps: 16,
            save_at: 5,
            checkpoint_leg: 1,
            resume_from: 11,
            compact_at: 12,
            pots: BTreeMap::from([(7, 200), (13, 150)]),
            batches: vec![
                vec![Leg::Open(21, 40), Leg::Move(7, 21, 25), Leg::Close],
                vec![
                    Leg::Move(13, 21, 15),
                    Leg::Move(21, 7, 5),
                    Leg::Close,
                ],
                vec![Leg::Open(28, 60), Leg::Move(7, 28, 30), Leg::Close],
                vec![Leg::Move(28, 13, 12), Leg::Close],
                vec![
                    Leg::Move(7, 28, 8),
                    Leg::Move(13, 21, 10),
                    Leg::Close,
                ],
                vec![Leg::Retire(21), Leg::Move(28, 7, 20), Leg::Close],
                vec![Leg::Move(13, 28, 7), Leg::Close],
                vec![Leg::Open(35, 45), Leg::Move(28, 35, 15), Leg::Close],
            ],
        },
        Scenario {
            name: "slate_purge_arc",
            steps: 18,
            save_at: 6,
            checkpoint_leg: 1,
            resume_from: 12,
            compact_at: 14,
            pots: BTreeMap::from([(5, 90), (9, 110), (14, 70)]),
            batches: vec![
                vec![Leg::Open(22, 55), Leg::Move(5, 22, 20), Leg::Close],
                vec![Leg::Move(9, 22, 18), Leg::Close],
                vec![
                    Leg::Move(14, 22, 12),
                    Leg::Move(22, 5, 8),
                    Leg::Close,
                ],
                vec![Leg::Retire(22), Leg::Move(9, 14, 6), Leg::Close],
                vec![Leg::Open(33, 40), Leg::Move(5, 33, 15), Leg::Close],
                vec![
                    Leg::Move(14, 33, 10),
                    Leg::Move(33, 9, 5),
                    Leg::Close,
                ],
                vec![Leg::Retire(33), Leg::Move(5, 14, 12), Leg::Close],
                vec![Leg::Open(41, 35), Leg::Move(9, 41, 20), Leg::Close],
            ],
        },
        Scenario {
            name: "brass_split_ladder",
            steps: 20,
            save_at: 7,
            checkpoint_leg: 1,
            resume_from: 15,
            compact_at: 16,
            pots: BTreeMap::from([(3, 160), (8, 140), (12, 100)]),
            batches: vec![
                vec![Leg::Open(17, 75), Leg::Move(3, 17, 30), Leg::Close],
                vec![Leg::Move(8, 17, 20), Leg::Close],
                vec![
                    Leg::Open(24, 50),
                    Leg::Move(12, 24, 25),
                    Leg::Move(17, 24, 10),
                    Leg::Close,
                ],
                vec![Leg::Move(24, 3, 15), Leg::Close],
                vec![
                    Leg::Move(8, 12, 18),
                    Leg::Move(3, 24, 12),
                    Leg::Close,
                ],
                vec![Leg::Retire(17), Leg::Move(24, 8, 14), Leg::Close],
                vec![Leg::Open(29, 65), Leg::Move(12, 29, 22), Leg::Close],
                vec![
                    Leg::Move(29, 3, 9),
                    Leg::Move(8, 29, 11),
                    Leg::Close,
                ],
                vec![Leg::Retire(24), Leg::Move(29, 12, 8), Leg::Close],
            ],
        },
        Scenario {
            name: "iron_cross_weave",
            steps: 17,
            save_at: 2,
            checkpoint_leg: 2,
            resume_from: 10,
            compact_at: 8,
            pots: BTreeMap::from([(6, 130), (15, 95)]),
            batches: vec![
                vec![Leg::Open(26, 45), Leg::Move(6, 26, 18), Leg::Close],
                vec![Leg::Move(15, 26, 12), Leg::Close],
                vec![
                    Leg::Open(38, 35),
                    Leg::Move(26, 38, 10),
                    Leg::Move(6, 38, 8),
                    Leg::Close,
                ],
                vec![Leg::Close, Leg::Move(38, 15, 6), Leg::Close],
                vec![Leg::Retire(26), Leg::Move(38, 6, 14), Leg::Close],
                vec![Leg::Open(47, 28), Leg::Move(15, 47, 9), Leg::Close],
                vec![
                    Leg::Move(6, 47, 11),
                    Leg::Move(38, 15, 5),
                    Leg::Close,
                ],
                vec![Leg::Retire(38), Leg::Move(47, 6, 7), Leg::Close],
            ],
        },
        Scenario {
            name: "mercury_gate_fold",
            steps: 16,
            save_at: 5,
            checkpoint_leg: 1,
            resume_from: 12,
            compact_at: 11,
            pots: BTreeMap::from([(10, 180), (16, 120)]),
            batches: vec![
                vec![Leg::Open(30, 50), Leg::Move(10, 30, 25), Leg::Close],
                vec![Leg::Move(16, 30, 15), Leg::Close],
                vec![Leg::Open(42, 40), Leg::Move(30, 42, 20), Leg::Close],
                vec![Leg::Move(42, 10, 12), Leg::Close],
                vec![
                    Leg::Move(10, 42, 8),
                    Leg::Move(16, 30, 10),
                    Leg::Close,
                ],
                vec![Leg::Retire(30), Leg::Move(42, 16, 6), Leg::Close],
                vec![Leg::Open(55, 35), Leg::Move(10, 55, 14), Leg::Close],
                vec![
                    Leg::Move(55, 42, 9),
                    Leg::Move(42, 10, 5),
                    Leg::Close,
                ],
            ],
        },
    ]
}

fn probe_scenarios() -> Vec<Scenario> {
    vec![
        Scenario {
            name: "quartz_ledger_skew",
            steps: 15,
            save_at: 3,
            checkpoint_leg: 0,
            resume_from: 10,
            compact_at: 8,
            pots: BTreeMap::from([(4, 100), (18, 60)]),
            batches: vec![
                vec![Leg::Open(27, 40), Leg::Move(4, 27, 15), Leg::Close],
                vec![Leg::Move(18, 27, 10), Leg::Close],
                vec![
                    Leg::Move(4, 18, 12),
                    Leg::Move(27, 4, 5),
                    Leg::Close,
                ],
                vec![
                    Leg::Move(18, 27, 8),
                    Leg::Move(4, 27, 6),
                    Leg::Close,
                ],
                vec![Leg::Retire(27), Leg::Move(18, 4, 9), Leg::Close],
                vec![Leg::Open(36, 30), Leg::Move(4, 36, 11), Leg::Close],
                vec![Leg::Move(36, 18, 7), Leg::Close],
            ],
        },
        Scenario {
            name: "obsidian_tail_fold",
            steps: 19,
            save_at: 4,
            checkpoint_leg: 2,
            resume_from: 14,
            compact_at: 10,
            pots: BTreeMap::from([(2, 150), (20, 90)]),
            batches: vec![
                vec![Leg::Open(25, 55), Leg::Move(2, 25, 20), Leg::Close],
                vec![Leg::Move(20, 25, 14), Leg::Close],
                vec![
                    Leg::Open(39, 45),
                    Leg::Move(25, 39, 18),
                    Leg::Move(2, 39, 9),
                    Leg::Close,
                ],
                vec![Leg::Move(39, 20, 11), Leg::Close],
                vec![
                    Leg::Move(20, 39, 8),
                    Leg::Move(2, 25, 10),
                    Leg::Move(39, 2, 6),
                    Leg::Close,
                ],
                vec![Leg::Retire(25), Leg::Move(39, 20, 5), Leg::Close],
                vec![Leg::Open(48, 35), Leg::Move(2, 48, 13), Leg::Close],
                vec![
                    Leg::Move(48, 39, 9),
                    Leg::Move(20, 48, 8),
                    Leg::Close,
                ],
                vec![Leg::Retire(39), Leg::Move(48, 2, 6), Leg::Close],
            ],
        },
    ]
}
