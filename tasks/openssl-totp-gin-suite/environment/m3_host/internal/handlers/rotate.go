package handlers

import (
	"encoding/hex"
	"net/http"

	"github.com/gin-gonic/gin"

	"m3_host/internal/store"
)

type RotateHandler struct {
	Store *store.AccountStore
}

type rotateRequest struct {
	AccountID string `json:"account_id"`
}

type rotateResponse struct {
	AccountID       string `json:"account_id"`
	SigningMaterial string `json:"signing_material"`
}

func (h *RotateHandler) Post(c *gin.Context) {
	var req rotateRequest
	if err := c.BindJSON(&req); err != nil || req.AccountID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "bad_request", "detail": "account_id required"}})
		return
	}
	acct, err := h.Store.RotateSigning(req.AccountID)
	if err == store.ErrMissing {
		c.JSON(http.StatusNotFound, gin.H{"error": gin.H{"code": "account_missing", "detail": "unknown account"}})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": gin.H{"code": "internal", "detail": "rotate failed"}})
		return
	}
	c.JSON(http.StatusOK, rotateResponse{
		AccountID:       acct.ID,
		SigningMaterial: hex.EncodeToString(acct.SigningMaterial),
	})
}
