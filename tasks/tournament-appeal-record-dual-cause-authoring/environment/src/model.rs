#[derive(Clone, Debug)]
pub struct Player {
    pub id: String,
    pub key: String,
    pub registered: u32,
    pub revoked: Option<u32>,
}

#[derive(Clone, Debug)]
pub struct MatchRecord {
    pub id: String,
    pub epoch: u32,
    pub format: String,
    pub home: String,
    pub away: String,
    pub signature: String,
    pub declared: String,
    pub moves: Vec<String>,
}

#[derive(Clone, Debug)]
pub struct AppealRecord {
    pub id: String,
    pub target: String,
    pub epoch: u32,
    pub replay_epoch: u32,
    pub signature: String,
    pub declared: String,
    pub moves: Vec<String>,
}

#[derive(Clone, Debug)]
pub struct Case {
    pub id: String,
    pub players: Vec<Player>,
    pub matches: Vec<MatchRecord>,
    pub appeals: Vec<AppealRecord>,
}

#[derive(Clone, Debug)]
pub struct MoveTrace {
    pub raw: String,
    pub actor: String,
    pub points: u32,
    pub annotation: String,
    pub legal: bool,
    pub reason: String,
}

#[derive(Clone, Debug)]
pub struct MatchEvaluation {
    pub id: String,
    pub home: String,
    pub away: String,
    pub status: String,
    pub epoch_used: u32,
    pub winner: Option<String>,
    pub score_home: u32,
    pub score_away: u32,
    pub errors: Vec<String>,
    pub move_trace: Vec<MoveTrace>,
}
