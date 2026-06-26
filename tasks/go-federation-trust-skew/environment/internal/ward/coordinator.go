package ward

import (
	"fedenv/parcel/realm"
	"fedenv/relay/alias"
	"fedenv/tally/spool"
)

type Engine struct {
	cfg        Config
	sp         *spool.Store
	reg        *realm.Registry
	mp         *alias.MapStore
	tableEpoch uint64
}

func NewEngine(cfg Config) *Engine {
	reg := realm.NewRegistry(cfg.LocalRealm)
	reg.Allow(cfg.LocalRealm)
	return &Engine{
		cfg:        cfg,
		sp:         spool.NewStore(),
		reg:        reg,
		mp:         alias.NewMapStore(),
		tableEpoch: 0,
	}
}

func (e *Engine) Config() Config       { return e.cfg }
func (e *Engine) Spool() *spool.Store  { return e.sp }
func (e *Engine) Map() *alias.MapStore { return e.mp }

func (e *Engine) InstallKey(kid string, gen uint64, key []byte) {
	e.sp.Install(kid, gen, key)
}

func (e *Engine) RotateKey(kid string, gen uint64, key []byte) {
	e.sp.Rotate(kid, gen, key)
}

func (e *Engine) ReloadMap(mapping map[string]string) {
	e.mp.Reload(mapping)
}

func (e *Engine) Admit(c Claim) Outcome {
	if !checkWindow(e.cfg, c) {
		return Outcome{Code: "DENY_TIME_WINDOW"}
	}
	key, ok := pickKey(e.sp, c)
	if !ok {
		return Outcome{Code: "DENY_STALE_KEY", UsedGen: c.Gen}
	}
	if !Match(key, c) {
		return Outcome{Code: "DENY_MAC", UsedGen: c.Gen}
	}
	if !realmMatches(e.cfg, c.Realm) {
		return Outcome{Code: "DENY_REALM"}
	}
	principal, ok, mapGen := resolveAlias(e, c.ExtID)
	if !ok {
		return Outcome{Code: "DENY_ALIAS"}
	}
	return Outcome{Code: "ADMIT", Principal: principal, UsedGen: c.Gen, UsedMapGen: mapGen}
}
