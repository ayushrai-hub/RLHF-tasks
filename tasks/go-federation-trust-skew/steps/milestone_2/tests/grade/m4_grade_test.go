package ward_test

import (
	"sync"
	"testing"
	"time"

	"fedenv/internal/ward"
)

const (
	kidAlpha = "k-alpha"
	baseNB   = int64(100_000)
	baseNA   = int64(110_000)
	anchorOK = int64(105_000)
)

func newEng() *ward.Engine {
	return ward.NewEngine(ward.DefaultConfig())
}

func keyFor(gen uint64) []byte {
	return []byte{byte(gen), byte(gen + 1), byte(gen + 2), byte(gen + 3)}
}

func claim(gen uint64, anchor int64, realm, ext string) ward.Claim {
	c := ward.Claim{
		Kid: kidAlpha, Gen: gen, Realm: realm, ExtID: ext,
		AnchorMs: anchor, NotBefore: baseNB, NotAfter: baseNA,
	}
	e := newEng()
	e.InstallKey(kidAlpha, gen, keyFor(gen))
	c.Sig = ward.Sign(keyFor(gen), c)
	return c
}

func freshClaim(e *ward.Engine, gen uint64, anchor int64, realm, ext string) ward.Claim {
	c := ward.Claim{
		Kid: kidAlpha, Gen: gen, Realm: realm, ExtID: ext,
		AnchorMs: anchor, NotBefore: baseNB, NotAfter: baseNA,
	}
	key, _ := e.Spool().Row(kidAlpha, gen)
	c.Sig = ward.Sign(key.Key, c)
	return c
}

func setupBasic(e *ward.Engine) {
	e.InstallKey(kidAlpha, 1, keyFor(1))
	e.ReloadMap(map[string]string{"ext-1": "principal-a"})
}

func TestWard_T01(t *testing.T) {
	e := newEng()
	setupBasic(e)
	c := freshClaim(e, 1, anchorOK, "svc://payments.local", "ext-1")
	out := e.Admit(c)
	if out.Code != "ADMIT" || out.Principal != "principal-a" {
		t.Fatalf("T01 code=%s principal=%s", out.Code, out.Principal)
	}
}

func TestWard_T02(t *testing.T) {
	e := newEng()
	setupBasic(e)
	edge := baseNB - ward.DefaultSlack.Milliseconds()
	c := freshClaim(e, 1, edge, "svc://payments.local", "ext-1")
	out := e.Admit(c)
	if out.Code != "ADMIT" {
		t.Fatalf("T02 edge slack low code=%s want ADMIT", out.Code)
	}
}

func TestWard_T03(t *testing.T) {
	e := newEng()
	setupBasic(e)
	edge := baseNB - ward.DefaultSlack.Milliseconds() - 1
	c := freshClaim(e, 1, edge, "svc://payments.local", "ext-1")
	out := e.Admit(c)
	if out.Code != "DENY_TIME_WINDOW" {
		t.Fatalf("T03 below slack code=%s want DENY_TIME_WINDOW", out.Code)
	}
}

func TestWard_T04(t *testing.T) {
	e := newEng()
	setupBasic(e)
	edge := baseNA + ward.DefaultSlack.Milliseconds()
	c := freshClaim(e, 1, edge, "svc://payments.local", "ext-1")
	out := e.Admit(c)
	if out.Code != "ADMIT" {
		t.Fatalf("T04 edge slack high code=%s want ADMIT", out.Code)
	}
}

func TestWard_T05(t *testing.T) {
	e := newEng()
	setupBasic(e)
	edge := baseNA + ward.DefaultSlack.Milliseconds() + 1
	c := freshClaim(e, 1, edge, "svc://payments.local", "ext-1")
	out := e.Admit(c)
	if out.Code != "DENY_TIME_WINDOW" {
		t.Fatalf("T05 above slack code=%s want DENY_TIME_WINDOW", out.Code)
	}
}

func TestWard_T06(t *testing.T) {
	e := newEng()
	setupBasic(e)
	c := freshClaim(e, 1, baseNB-ward.DefaultSlack.Milliseconds()-1, "svc://payments.local", "ext-1")
	out := e.Admit(c)
	if out.Code != "DENY_TIME_WINDOW" {
		t.Fatalf("T06 before nb code=%s want DENY_TIME_WINDOW", out.Code)
	}
}

func TestWard_T07(t *testing.T) {
	e := newEng()
	setupBasic(e)
	c := freshClaim(e, 1, baseNA+1, "svc://payments.local", "ext-1")
	out := e.Admit(c)
	if out.Code != "ADMIT" {
		t.Fatalf("T07 inside upper slack code=%s want ADMIT", out.Code)
	}
}

func TestWard_T08(t *testing.T) {
	e := newEng()
	setupBasic(e)
	c := freshClaim(e, 1, baseNB, "svc://payments.local", "ext-1")
	out := e.Admit(c)
	if out.Code != "ADMIT" {
		t.Fatalf("T08 nb boundary code=%s want ADMIT", out.Code)
	}
}

func TestWard_T09(t *testing.T) {
	e := newEng()
	setupBasic(e)
	c := freshClaim(e, 1, anchorOK, "svc://payments.local", "ext-1")
	out := e.Admit(c)
	if out.Code != "ADMIT" || out.UsedGen != 1 {
		t.Fatalf("T09 gen1 code=%s gen=%d", out.Code, out.UsedGen)
	}
}

func TestWard_T10(t *testing.T) {
	e := newEng()
	setupBasic(e)
	stale := freshClaim(e, 1, anchorOK, "svc://payments.local", "ext-1")
	e.RotateKey(kidAlpha, 2, keyFor(2))
	out := e.Admit(stale)
	if out.Code != "DENY_STALE_KEY" {
		t.Fatalf("T10 stale gen code=%s want DENY_STALE_KEY", out.Code)
	}
}

func TestWard_T11(t *testing.T) {
	e := newEng()
	setupBasic(e)
	e.RotateKey(kidAlpha, 2, keyFor(2))
	c := freshClaim(e, 2, anchorOK, "svc://payments.local", "ext-1")
	out := e.Admit(c)
	if out.Code != "ADMIT" || out.UsedGen != 2 {
		t.Fatalf("T11 live gen2 code=%s gen=%d", out.Code, out.UsedGen)
	}
}

func TestWard_T12(t *testing.T) {
	e := newEng()
	setupBasic(e)
	e.RotateKey(kidAlpha, 2, keyFor(2))
	c := ward.Claim{
		Kid: kidAlpha, Gen: 3, Realm: "svc://payments.local", ExtID: "ext-1",
		AnchorMs: anchorOK, NotBefore: baseNB, NotAfter: baseNA,
	}
	c.Sig = ward.Sign(keyFor(3), c)
	out := e.Admit(c)
	if out.Code != "DENY_STALE_KEY" {
		t.Fatalf("T12 future gen code=%s want DENY_STALE_KEY", out.Code)
	}
}

func TestWard_T13(t *testing.T) {
	e := newEng()
	setupBasic(e)
	e.RotateKey(kidAlpha, 2, keyFor(2))
	e.RotateKey(kidAlpha, 3, keyFor(3))
	c := freshClaim(e, 3, anchorOK, "svc://payments.local", "ext-1")
	out := e.Admit(c)
	if out.Code != "ADMIT" {
		t.Fatalf("T13 gen3 code=%s want ADMIT", out.Code)
	}
}

func TestWard_T14(t *testing.T) {
	e := newEng()
	setupBasic(e)
	e.RotateKey(kidAlpha, 2, keyFor(2))
	stale := freshClaim(e, 1, anchorOK, "svc://payments.local", "ext-1")
	if out := e.Admit(stale); out.Code != "DENY_STALE_KEY" {
		t.Fatalf("T14 first stale code=%s", out.Code)
	}
	fresh := freshClaim(e, 2, anchorOK, "svc://payments.local", "ext-1")
	if out := e.Admit(fresh); out.Code != "ADMIT" {
		t.Fatalf("T14 fresh code=%s", out.Code)
	}
}

func TestWard_T15(t *testing.T) {
	e := newEng()
	setupBasic(e)
	c := freshClaim(e, 1, anchorOK, "svc://payments.local", "ext-1")
	if e.Spool().LiveGen(kidAlpha) != 1 {
		t.Fatal("T15 live gen mismatch")
	}
	out := e.Admit(c)
	if out.Code != "ADMIT" {
		t.Fatalf("T15 pre-rotate code=%s", out.Code)
	}
}

func TestWard_T16(t *testing.T) {
	e := newEng()
	setupBasic(e)
	e.RotateKey(kidAlpha, 2, keyFor(2))
	for i := 0; i < 4; i++ {
		stale := freshClaim(e, 1, anchorOK, "svc://payments.local", "ext-1")
		if out := e.Admit(stale); out.Code != "DENY_STALE_KEY" {
			t.Fatalf("T16 iter %d stale code=%s", i, out.Code)
		}
	}
}

func TestWard_T17(t *testing.T) {
	e := newEng()
	setupBasic(e)
	c := freshClaim(e, 1, anchorOK, "svc://payments.local", "ext-1")
	out := e.Admit(c)
	if out.Code != "ADMIT" {
		t.Fatalf("T17 exact realm code=%s", out.Code)
	}
}

func TestWard_T18(t *testing.T) {
	e := newEng()
	setupBasic(e)
	c := freshClaim(e, 1, anchorOK, "SVC://Payments.Local/", "ext-1")
	out := e.Admit(c)
	if out.Code != "ADMIT" {
		t.Fatalf("T18 folded realm code=%s want ADMIT", out.Code)
	}
}

func TestWard_T19(t *testing.T) {
	e := newEng()
	setupBasic(e)
	c := freshClaim(e, 1, anchorOK, "svc://billing.local", "ext-1")
	out := e.Admit(c)
	if out.Code != "DENY_REALM" {
		t.Fatalf("T19 wrong realm code=%s want DENY_REALM", out.Code)
	}
}

func TestWard_T20(t *testing.T) {
	e := newEng()
	setupBasic(e)
	c := freshClaim(e, 1, anchorOK, "https://payments.local", "ext-1")
	out := e.Admit(c)
	if out.Code != "ADMIT" {
		t.Fatalf("T20 scheme fold code=%s want ADMIT", out.Code)
	}
}

func TestWard_T21(t *testing.T) {
	e := newEng()
	setupBasic(e)
	c := freshClaim(e, 1, anchorOK, "payments.local", "ext-1")
	out := e.Admit(c)
	if out.Code != "ADMIT" {
		t.Fatalf("T21 bare host code=%s want ADMIT", out.Code)
	}
}

func TestWard_T22(t *testing.T) {
	e := newEng()
	setupBasic(e)
	c := freshClaim(e, 1, anchorOK, "svc://payments.local/", "ext-1")
	out := e.Admit(c)
	if out.Code != "ADMIT" {
		t.Fatalf("T22 trailing slash code=%s want ADMIT", out.Code)
	}
}

func TestWard_T23(t *testing.T) {
	e := newEng()
	setupBasic(e)
	c := freshClaim(e, 1, anchorOK, "svc://other.local", "ext-1")
	out := e.Admit(c)
	if out.Code != "DENY_REALM" {
		t.Fatalf("T23 foreign realm code=%s", out.Code)
	}
}

func TestWard_T24(t *testing.T) {
	e := newEng()
	setupBasic(e)
	cases := []string{"HTTPS://PAYMENTS.LOCAL/", "svc://payments.local", "payments.local/"}
	for _, realm := range cases {
		c := freshClaim(e, 1, anchorOK, realm, "ext-1")
		if out := e.Admit(c); out.Code != "ADMIT" {
			t.Fatalf("T24 realm=%s code=%s", realm, out.Code)
		}
	}
}

func TestWard_T25(t *testing.T) {
	e := newEng()
	setupBasic(e)
	c := freshClaim(e, 1, anchorOK, "svc://payments.local", "ext-1")
	out := e.Admit(c)
	if out.Code != "ADMIT" || out.Principal != "principal-a" {
		t.Fatalf("T25 alias code=%s principal=%s", out.Code, out.Principal)
	}
}

func TestWard_T26(t *testing.T) {
	e := newEng()
	setupBasic(e)
	c1 := freshClaim(e, 1, anchorOK, "svc://payments.local", "ext-1")
	if out := e.Admit(c1); out.Principal != "principal-a" {
		t.Fatalf("T26 pre-reload principal=%s", out.Principal)
	}
	e.ReloadMap(map[string]string{"ext-1": "principal-b"})
	c2 := freshClaim(e, 1, anchorOK, "svc://payments.local", "ext-1")
	out := e.Admit(c2)
	if out.Code != "ADMIT" || out.Principal != "principal-b" {
		t.Fatalf("T26 post-reload code=%s principal=%s want principal-b", out.Code, out.Principal)
	}
}

func TestWard_T27(t *testing.T) {
	e := newEng()
	setupBasic(e)
	e.ReloadMap(map[string]string{"ext-2": "principal-z"})
	c := freshClaim(e, 1, anchorOK, "svc://payments.local", "ext-2")
	out := e.Admit(c)
	if out.Code != "ADMIT" || out.Principal != "principal-z" {
		t.Fatalf("T27 new ext code=%s principal=%s", out.Code, out.Principal)
	}
}

func TestWard_T28(t *testing.T) {
	e := newEng()
	setupBasic(e)
	c := freshClaim(e, 1, anchorOK, "svc://payments.local", "missing")
	out := e.Admit(c)
	if out.Code != "DENY_ALIAS" {
		t.Fatalf("T28 missing alias code=%s want DENY_ALIAS", out.Code)
	}
}

func TestWard_T29(t *testing.T) {
	e := newEng()
	setupBasic(e)
	before := e.Map().Generation()
	e.ReloadMap(map[string]string{"ext-1": "principal-b"})
	after := e.Map().Generation()
	if after != before+1 {
		t.Fatalf("T29 gen before=%d after=%d", before, after)
	}
	c := freshClaim(e, 1, anchorOK, "svc://payments.local", "ext-1")
	out := e.Admit(c)
	if out.UsedMapGen != after {
		t.Fatalf("T29 usedMapGen=%d want %d", out.UsedMapGen, after)
	}
}

func TestWard_T30(t *testing.T) {
	e := newEng()
	setupBasic(e)
	var wg sync.WaitGroup
	for i := 0; i < 8; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			m := map[string]string{"ext-1": "principal-race"}
			e.ReloadMap(m)
		}(i)
	}
	wg.Wait()
	c := freshClaim(e, 1, anchorOK, "svc://payments.local", "ext-1")
	out := e.Admit(c)
	if out.Code != "ADMIT" || out.Principal != "principal-race" {
		t.Fatalf("T30 race reload code=%s principal=%s", out.Code, out.Principal)
	}
}

func TestWard_T31(t *testing.T) {
	e := newEng()
	setupBasic(e)
	_ = e.Admit(freshClaim(e, 1, anchorOK, "svc://payments.local", "ext-1"))
	e.ReloadMap(map[string]string{"ext-1": "principal-c"})
	e.ReloadMap(map[string]string{"ext-1": "principal-d"})
	c := freshClaim(e, 1, anchorOK, "svc://payments.local", "ext-1")
	out := e.Admit(c)
	if out.Principal != "principal-d" {
		t.Fatalf("T31 double reload principal=%s", out.Principal)
	}
}

func TestWard_T32(t *testing.T) {
	e := newEng()
	setupBasic(e)
	// Warm cache under old generation
	_ = e.Admit(freshClaim(e, 1, anchorOK, "svc://payments.local", "ext-1"))
	e.ReloadMap(map[string]string{"ext-1": "principal-final"})
	// Force concurrent reads during reload
	var wg sync.WaitGroup
	errCh := make(chan string, 16)
	for i := 0; i < 16; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			c := freshClaim(e, 1, anchorOK, "svc://payments.local", "ext-1")
			out := e.Admit(c)
			if out.Code == "ADMIT" && out.Principal != "principal-final" {
				errCh <- out.Principal
			}
		}()
	}
	wg.Wait()
	close(errCh)
	for p := range errCh {
		t.Fatalf("T32 stale principal=%s want principal-final", p)
	}
}

func TestWard_T33(t *testing.T) {
	e := newEng()
	setupBasic(e)
	c := freshClaim(e, 1, anchorOK, "https://payments.local:443", "ext-1")
	out := e.Admit(c)
	if out.Code != "ADMIT" {
		t.Fatalf("T33 default port code=%s want ADMIT", out.Code)
	}
}

func TestWard_T34(t *testing.T) {
	e := newEng()
	setupBasic(e)
	e.RotateKey(kidAlpha, 2, keyFor(2))
	e.RotateKey(kidAlpha, 3, keyFor(3))
	e.RotateKey(kidAlpha, 4, keyFor(4))
	stale := freshClaim(e, 2, anchorOK, "svc://payments.local", "ext-1")
	if out := e.Admit(stale); out.Code != "DENY_STALE_KEY" {
		t.Fatalf("T34 stale gen2 code=%s want DENY_STALE_KEY", out.Code)
	}
	fresh := freshClaim(e, 4, anchorOK, "svc://payments.local", "ext-1")
	if out := e.Admit(fresh); out.Code != "ADMIT" {
		t.Fatalf("T34 live gen4 code=%s want ADMIT", out.Code)
	}
}

func TestWard_T35(t *testing.T) {
	e := newEng()
	setupBasic(e)
	e.RotateKey(kidAlpha, 2, keyFor(2))
	e.RotateKey(kidAlpha, 3, keyFor(3))
	c := freshClaim(e, 3, anchorOK, "svc://payments.local", "ext-1")
	out := e.Admit(c)
	if out.Code != "ADMIT" || out.UsedGen != 3 {
		t.Fatalf("T35 live gen3 material code=%s gen=%d", out.Code, out.UsedGen)
	}
}

func TestWard_T36(t *testing.T) {
	e := newEng()
	setupBasic(e)
	e.ReloadMap(map[string]string{"ext-1": "principal-snap"})
	c := freshClaim(e, 1, anchorOK, "svc://payments.local", "ext-1")
	out := e.Admit(c)
	if out.Code != "ADMIT" || out.Principal != "principal-snap" {
		t.Fatalf("T36 snap reload code=%s principal=%s", out.Code, out.Principal)
	}
	if out.UsedMapGen != e.Map().Generation() {
		t.Fatalf("T36 usedMapGen=%d live=%d", out.UsedMapGen, e.Map().Generation())
	}
}

func TestWard_ProbeFresh(t *testing.T) {
	e := newEng()
	setupBasic(e)
	c := freshClaim(e, 1, anchorOK, "svc://payments.local", "ext-1")
	out := e.Admit(c)
	if out.Code != "ADMIT" {
		t.Fatalf("probe fresh code=%s", out.Code)
	}
}

func TestWard_RaceReload(t *testing.T) {
	e := newEng()
	setupBasic(e)
	e.ReloadMap(map[string]string{"ext-1": "principal-race"})
	var wg sync.WaitGroup
	stop := make(chan struct{})
	wg.Add(1)
	go func() {
		defer wg.Done()
		for i := 0; i < 24; i++ {
			select {
			case <-stop:
				return
			default:
				e.ReloadMap(map[string]string{"ext-1": "principal-race"})
			}
		}
	}()
	for i := 0; i < 16; i++ {
		c := freshClaim(e, 1, anchorOK, "svc://payments.local", "ext-1")
		out := e.Admit(c)
		if out.Code == "ADMIT" && out.Principal != "principal-race" {
			close(stop)
			wg.Wait()
			t.Fatalf("race stale principal=%s", out.Principal)
		}
	}
	close(stop)
	wg.Wait()
}

func init() {
	_ = time.Millisecond
}
