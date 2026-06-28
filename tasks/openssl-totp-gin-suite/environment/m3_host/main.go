package main

import (
	"time"

	"github.com/gin-gonic/gin"

	"m3_host/internal/config"
	"m3_host/internal/handlers"
	"m3_host/internal/store"
)

func main() {
	gin.SetMode(gin.ReleaseMode)
	cfg := config.Load()
	st := store.NewAccountStore()

	enroll := &handlers.EnrollHandler{Store: st}
	mfa := &handlers.MFAHandler{Store: st, Config: cfg}
	verify := &handlers.VerifyHandler{Store: st, Config: cfg}
	rotate := &handlers.RotateHandler{Store: st}

	r := gin.New()
	r.Use(clockMiddleware())

	r.POST("/v1/accounts/enroll", enroll.Post)
	r.POST("/v1/accounts/rotate", rotate.Post)
	r.POST("/v1/sessions/mfa", mfa.Post)
	r.POST("/v1/sessions/verify", verify.Post)
	r.GET("/healthz", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "ok"})
	})

	_ = r.Run(cfg.ListenAddr)
}

func clockMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		now := time.Now().Unix()
		if v := config.ClockEpoch(); v > 0 {
			now = v
		}
		c.Set("now_epoch", now)
		c.Next()
	}
}
