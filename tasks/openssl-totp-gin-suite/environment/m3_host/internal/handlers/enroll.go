package handlers

import (
	"crypto/rand"
	"encoding/hex"
	"net/http"

	"github.com/gin-gonic/gin"

	"m3_host/internal/store"
)

type EnrollHandler struct {
	Store *store.AccountStore
}

type enrollRequest struct {
	Handle string `json:"handle"`
}

type enrollResponse struct {
	AccountID       string `json:"account_id"`
	WrappedSecret   string `json:"wrapped_secret"`
	SigningMaterial string `json:"signing_material"`
}

func (h *EnrollHandler) Post(c *gin.Context) {
	var req enrollRequest
	if err := c.BindJSON(&req); err != nil || req.Handle == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "bad_request", "detail": "handle required"}})
		return
	}
	secret, err := randomSecret()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": gin.H{"code": "internal", "detail": "secret generation failed"}})
		return
	}
	acct, err := h.Store.Enroll(req.Handle, secret)
	if err == store.ErrConflict {
		c.JSON(http.StatusConflict, gin.H{"error": gin.H{"code": "enroll_conflict", "detail": "handle already enrolled"}})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": gin.H{"code": "internal", "detail": "enroll failed"}})
		return
	}
	c.JSON(http.StatusOK, enrollResponse{
		AccountID:       acct.ID,
		WrappedSecret:   base32Encode(acct.SecretRaw),
		SigningMaterial: hex.EncodeToString(acct.SigningMaterial),
	})
}

func randomSecret() ([]byte, error) {
	buf := make([]byte, 20)
	if _, err := rand.Read(buf); err != nil {
		return nil, err
	}
	return buf, nil
}

func base32Encode(raw []byte) string {
	const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
	if len(raw) == 0 {
		return ""
	}
	var out []byte
	var buffer uint32
	bits := 0
	for _, b := range raw {
		buffer = (buffer << 8) | uint32(b)
		bits += 8
		for bits >= 5 {
			bits -= 5
			out = append(out, alphabet[(buffer>>bits)&31])
		}
	}
	if bits > 0 {
		out = append(out, alphabet[(buffer<<(5-bits))&31])
	}
	for len(out)%8 != 0 {
		out = append(out, '=')
	}
	return string(out)
}
