package ward

import "time"

const DefaultSlack = 5 * time.Second

type Config struct {
	LocalRealm string
	Slack      time.Duration
}

func DefaultConfig() Config {
	return Config{LocalRealm: "svc://payments.local", Slack: DefaultSlack}
}

type Claim struct {
	Kid      string
	Gen      uint64
	Realm    string
	ExtID    string
	AnchorMs int64
	NotBefore int64
	NotAfter  int64
	Sig      []byte
}

type Outcome struct {
	Code       string
	Principal  string
	UsedGen    uint64
	UsedMapGen uint64
}
