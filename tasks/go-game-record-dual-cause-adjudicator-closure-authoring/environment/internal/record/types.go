package record

type Rulebook struct {
	Ruleset             string  `json:"ruleset"`
	BoardSize           int     `json:"board_size"`
	Komi                float64 `json:"komi"`
	PassesToEnd         int     `json:"passes_to_end"`
	Scoring             string  `json:"scoring"`
	LegacyScoreNotation bool    `json:"legacy_score_notation"`
}

type Move struct {
	Number int    `json:"number"`
	Color  string `json:"color"`
	Point  string `json:"point"`
}

type Variation struct {
	Name     string `json:"name"`
	FromMove int    `json:"from_move"`
	Moves    []Move `json:"moves"`
}

type Score struct {
	Legacy    bool    `json:"legacy"`
	BlackArea int     `json:"black_area,omitempty"`
	WhiteArea int     `json:"white_area,omitempty"`
	Winner    string  `json:"winner"`
	Margin    float64 `json:"margin"`
	Raw       string  `json:"raw"`
}

type GameRecord struct {
	RecordID   string      `json:"record_id"`
	Ruleset    string      `json:"ruleset"`
	BoardSize  int         `json:"board_size"`
	Komi       float64     `json:"komi"`
	Main       []Move      `json:"main"`
	Variations []Variation `json:"variations"`
	Score      Score       `json:"score"`
	ResultRaw  string      `json:"result_raw"`
	Path       string      `json:"path"`
}

type VariationReplay struct {
	Name            string   `json:"name"`
	FromMove        int      `json:"from_move"`
	StateHash       string   `json:"state_hash"`
	BranchOnlyMoves []string `json:"branch_only_moves"`
	BranchLeakCount int      `json:"branch_leak_count"`
}

type ReplayResult struct {
	RecordID             string            `json:"record_id"`
	Ruleset              string            `json:"ruleset"`
	MainMoveCount        int               `json:"main_move_count"`
	FinalStateHash       string            `json:"final_state_hash"`
	PassesToClose        int               `json:"passes_to_close"`
	TerminalPassMoveNums []int             `json:"terminal_pass_move_numbers"`
	Winner               string            `json:"winner"`
	Margin               float64           `json:"margin"`
	LegacyScoreNotation  bool              `json:"legacy_score_notation"`
	VariationReplays     []VariationReplay `json:"variation_replays"`
}
