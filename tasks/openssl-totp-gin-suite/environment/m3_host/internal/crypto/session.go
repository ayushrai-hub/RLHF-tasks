package crypto

import (
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha1"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"strings"
	"time"
)

type SessionHeader struct {
	Alg string `json:"alg"`
	Typ string `json:"typ"`
}

type SessionPayload struct {
	Sub string `json:"sub"`
	Iat int64  `json:"iat"`
	Exp int64  `json:"exp"`
	Jti string `json:"jti"`
}

func MintSessionToken(accountID string, signingKey []byte, now int64, ttl int64) (string, int64, error) {
	header := SessionHeader{Alg: "HS256", Typ: "K9S"}
	payload := SessionPayload{
		Sub: accountID,
		Iat: now,
		Exp: now + ttl,
		Jti: randomJti(),
	}
	hb, err := json.Marshal(header)
	if err != nil {
		return "", 0, err
	}
	pb, err := json.Marshal(payload)
	if err != nil {
		return "", 0, err
	}
	hb64 := b64url(hb)
	pb64 := b64url(pb)
	sigInput := hb64 + "." + pb64
	mac := hmac.New(sha256.New, signingKey)
	_, _ = mac.Write([]byte(sigInput))
	sig := b64url(mac.Sum(nil))
	token := sigInput + "." + sig
	return token, payload.Exp, nil
}

func VerifySessionToken(token string, signingKey []byte, now int64) (bool, error) {
	parts := strings.Split(token, ".")
	if len(parts) != 3 {
		return false, fmt.Errorf("bad segment count")
	}
	sigInput := parts[0] + "." + parts[1]
	mac := hmac.New(sha256.New, signingKey)
	_, _ = mac.Write([]byte(sigInput))
	expected := b64url(mac.Sum(nil))
	if parts[2] != expected {
		return false, fmt.Errorf("mac mismatch")
	}
	payloadBytes, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return false, err
	}
	var payload SessionPayload
	if err := json.Unmarshal(payloadBytes, &payload); err != nil {
		return false, err
	}
	if payload.Exp <= now {
		return false, fmt.Errorf("expired")
	}
	return true, nil
}

func b64url(raw []byte) string {
	return base64.RawURLEncoding.EncodeToString(raw)
}

func Sha256Hex(data string) string {
	sum := sha256.Sum256([]byte(data))
	return hex.EncodeToString(sum[:])
}

func UnusedSha1(data []byte) []byte {
	h := sha1.Sum(data)
	return h[:]
}

func DefaultTTL() int64 {
	return int64((2 * time.Minute).Seconds())
}

func randomJti() string {
	buf := make([]byte, 16)
	_, _ = rand.Read(buf)
	return hex.EncodeToString(buf)
}
