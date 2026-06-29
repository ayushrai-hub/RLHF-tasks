package handlers

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"

	"m3_host/internal/config"
	"m3_host/internal/crypto"
	"m3_host/internal/store"
)

type MFAHandler struct {
	Store  *store.AccountStore
	Config config.HostConfig
}

type mfaRequest struct {
	AccountID string `json:"account_id"`
	Passcode  string `json:"passcode"`
}

type mfaResponse struct {
	SessionToken string `json:"session_token"`
	ExpiresAt    int64  `json:"expires_at"`
}

func (h *MFAHandler) Post(c *gin.Context) {
	var req mfaRequest
	if err := c.BindJSON(&req); err != nil || req.AccountID == "" || req.Passcode == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "bad_request", "detail": "account_id and passcode required"}})
		return
	}
	acct, err := h.Store.GetByID(req.AccountID)
	if err == store.ErrMissing {
		c.JSON(http.StatusNotFound, gin.H{"error": gin.H{"code": "account_missing", "detail": "unknown account"}})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": gin.H{"code": "internal", "detail": "lookup failed"}})
		return
	}
	epoch := resolveEpoch(c)
	if !crypto.PasscodeValid(acct.SecretRaw, req.Passcode, epoch, h.Config.StepSeconds, h.Config.StepWindow, h.Config.Digits) {
		c.JSON(http.StatusUnauthorized, gin.H{"error": gin.H{"code": "totp_reject", "detail": "passcode rejected"}})
		return
	}
	token, exp, err := crypto.MintSessionToken(acct.ID, acct.SigningMaterial, epoch, crypto.DefaultTTL())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": gin.H{"code": "internal", "detail": "token mint failed"}})
		return
	}
	c.JSON(http.StatusOK, mfaResponse{SessionToken: token, ExpiresAt: exp})
}

func resolveEpoch(c *gin.Context) int64 {
	if v := config.ClockEpoch(); v > 0 {
		return v
	}
	if hdr := c.GetHeader("X-Clock-Epoch"); hdr != "" {
		if n, err := strconv.ParseInt(hdr, 10, 64); err == nil {
			return n
		}
	}
	return c.GetInt64("now_epoch")
}
