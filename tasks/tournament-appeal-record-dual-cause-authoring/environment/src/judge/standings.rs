use std::collections::{BTreeMap, HashMap};

use crate::adjudicate::record;
use crate::appeal::replay;
use crate::model::{Case, MatchEvaluation, Player};
use crate::proof::{json_string, json_string_array, source_fingerprint};

#[derive(Clone, Default)]
struct Standing {
    player: String,
    wins: u32,
    losses: u32,
    draws: u32,
    points: u32,
}

pub fn build_proof(raw_input: &str, cases: &[Case]) -> String {
    let mut case_docs: Vec<String> = Vec::new();
    for case in cases {
        case_docs.push(render_case(case));
    }
    format!(
        "{{\n  \"schema\":\"rookline.tournament-appeal-proof.v1\",\n  \"generated_by\":\"rookline prove\",\n  \"source_fingerprint\":{},\n  \"case_count\":{},\n  \"cases\":[\n{}\n  ]\n}}\n",
        json_string(&source_fingerprint(raw_input)),
        cases.len(),
        case_docs.join(",\n")
    )
}

fn render_case(case: &Case) -> String {
    let players_by_id: HashMap<String, Player> = case
        .players
        .iter()
        .cloned()
        .map(|player| (player.id.clone(), player))
        .collect();
    let appeals_by_target: HashMap<String, &crate::model::AppealRecord> = case
        .appeals
        .iter()
        .map(|appeal| (appeal.target.clone(), appeal))
        .collect();

    let mut evaluations: Vec<MatchEvaluation> = Vec::new();
    for record_item in &case.matches {
        if let Some(appeal) = appeals_by_target.get(&record_item.id) {
            evaluations.push(replay::evaluate_replay(record_item, appeal, &players_by_id));
        } else {
            evaluations.push(record::evaluate_record(
                record_item,
                &players_by_id,
                record_item.epoch,
                "revoked_at_record_epoch",
            ));
        }
    }

    let standings = build_standings(&case.players, &evaluations);
    let match_json: Vec<String> = evaluations.iter().map(render_match).collect();
    let appeal_json: Vec<String> = case
        .appeals
        .iter()
        .map(|appeal| {
            let status = evaluations
                .iter()
                .find(|evaluation| evaluation.id == appeal.target)
                .map(|evaluation| evaluation.status.as_str())
                .unwrap_or("target_missing");
            format!(
                "{{\"id\":{},\"target\":{},\"epoch\":{},\"replay_epoch\":{},\"status\":{}}}",
                json_string(&appeal.id),
                json_string(&appeal.target),
                appeal.epoch,
                appeal.replay_epoch,
                json_string(status)
            )
        })
        .collect();
    let standing_json: Vec<String> = standings.iter().map(render_standing).collect();
    let accepted_count = evaluations
        .iter()
        .filter(|evaluation| evaluation.status == "accepted" || evaluation.status == "replay_accepted")
        .count();

    format!(
        "    {{\n      \"case_id\":{},\n      \"judge\":{{\"verdict\":\"accepted\",\"errors\":[],\"accepted_match_count\":{}}},\n      \"matches\":[{}],\n      \"appeals\":[{}],\n      \"standings\":[{}]\n    }}",
        json_string(&case.id),
        accepted_count,
        match_json.join(","),
        appeal_json.join(","),
        standing_json.join(",")
    )
}

fn build_standings(players: &[Player], evaluations: &[MatchEvaluation]) -> Vec<Standing> {
    let mut table: BTreeMap<String, Standing> = BTreeMap::new();
    for player in players {
        table.insert(
            player.id.clone(),
            Standing {
                player: player.id.clone(),
                ..Standing::default()
            },
        );
    }

    for evaluation in evaluations {
        if evaluation.status != "accepted" && evaluation.status != "replay_accepted" {
            continue;
        }
        match &evaluation.winner {
            Some(winner) => {
                let loser = if *winner == evaluation.home {
                    evaluation.away.clone()
                } else {
                    evaluation.home.clone()
                };
                if let Some(entry) = table.get_mut(winner) {
                    entry.wins += 1;
                    entry.points += 3;
                }
                if let Some(entry) = table.get_mut(&loser) {
                    entry.losses += 1;
                }
            }
            None => {
                if let Some(entry) = table.get_mut(&evaluation.home) {
                    entry.draws += 1;
                    entry.points += 1;
                }
                if let Some(entry) = table.get_mut(&evaluation.away) {
                    entry.draws += 1;
                    entry.points += 1;
                }
            }
        }
    }

    let mut standings: Vec<Standing> = table.into_values().collect();
    standings.sort_by(|left, right| {
        right
            .points
            .cmp(&left.points)
            .then_with(|| right.wins.cmp(&left.wins))
            .then_with(|| left.player.cmp(&right.player))
    });
    standings
}

fn render_standing(standing: &Standing) -> String {
    format!(
        "{{\"player\":{},\"wins\":{},\"losses\":{},\"draws\":{},\"points\":{}}}",
        json_string(&standing.player),
        standing.wins,
        standing.losses,
        standing.draws,
        standing.points
    )
}

fn render_match(evaluation: &MatchEvaluation) -> String {
    let traces: Vec<String> = evaluation.move_trace.iter().map(render_trace).collect();
    let winner = match &evaluation.winner {
        Some(player) => json_string(player),
        None => "null".to_string(),
    };
    format!(
        "{{\"id\":{},\"home\":{},\"away\":{},\"status\":{},\"epoch_used\":{},\"winner\":{},\"score\":{{\"home\":{},\"away\":{}}},\"errors\":{},\"move_trace\":[{}]}}",
        json_string(&evaluation.id),
        json_string(&evaluation.home),
        json_string(&evaluation.away),
        json_string(&evaluation.status),
        evaluation.epoch_used,
        winner,
        evaluation.score_home,
        evaluation.score_away,
        json_string_array(&evaluation.errors),
        traces.join(",")
    )
}

fn render_trace(trace: &crate::model::MoveTrace) -> String {
    format!(
        "{{\"raw\":{},\"actor\":{},\"points\":{},\"annotation\":{},\"legal\":{},\"reason\":{}}}",
        json_string(&trace.raw),
        json_string(&trace.actor),
        trace.points,
        json_string(&trace.annotation),
        if trace.legal { "true" } else { "false" },
        json_string(&trace.reason)
    )
}
