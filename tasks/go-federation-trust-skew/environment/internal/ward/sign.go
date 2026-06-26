package ward

import (
	"crypto/hmac"
	"crypto/sha256"
	"fmt"
)

func payload(c Claim) []byte {
	return []byte(fmt.Sprintf("%s|%d|%s|%s|%d|%d|%d",
		c.Kid, c.Gen, c.Realm, c.ExtID, c.AnchorMs, c.NotBefore, c.NotAfter))
}

func Sign(key []byte, c Claim) []byte {
	m := hmac.New(sha256.New, key)
	_, _ = m.Write(payload(c))
	return m.Sum(nil)
}

func Match(key []byte, c Claim) bool {
	expect := Sign(key, c)
	return hmac.Equal(expect, c.Sig)
}
