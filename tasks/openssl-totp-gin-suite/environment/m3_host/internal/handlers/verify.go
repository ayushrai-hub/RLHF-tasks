package handlers

import (
	"encoding/hex"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"

	"m3_host/internal/config"
	"m3_host/internal/crypto"
	"m3_host/internal/store"
)

type VerifyHandler struct {
	Store  *store.AccountStore
	Config config.HostConfig
}

type verifyRequest struct {
	AccountID    string `json:"account_id"`
	SessionToken string `json:"session_token"`
}

type verifyResponse struct {
	Status string `json:"status"`
	Digest string `json:"digest"`
}

func (h *VerifyHandler) Post(c *gin.Context) {
	var req verifyRequest
	if err := c.BindJSON(&req); err != nil || req.AccountID == "" || req.SessionToken == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "bad_request", "detail": "account_id and session_token required"}})
		return
	}
	acct, err := h.Store.GetByID(req.AccountID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": gin.H{"code": "account_missing", "detail": "unknown account"}})
		return
	}
	epoch := resolveEpoch(c)
	ok, err := crypto.VerifySessionToken(req.SessionToken, acct.SigningMaterial, epoch)
	if err != nil || !ok {
		c.JSON(http.StatusUnauthorized, gin.H{"error": gin.H{"code": "seal_reject", "detail": "session seal rejected"}})
		return
	}
	c.JSON(http.StatusOK, verifyResponse{
		Status: "verified",
		Digest: crypto.Sha256Hex(req.SessionToken),
	})
}

func ParseSigningHex(s string) ([]byte, error) {
	return hex.DecodeString(s)
}

func ParseClockHeader(c *gin.Context) int64 {
	if hdr := c.GetHeader("X-Clock-Epoch"); hdr != "" {
		if n, err := strconv.ParseInt(hdr, 10, 64); err == nil {
			return n
		}
	}
	return 0
}
