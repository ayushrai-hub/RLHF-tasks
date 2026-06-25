package main

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
)

// decodeStrict decodes the JSON request body.
func decodeStrict(w http.ResponseWriter, r *http.Request, dst interface{}) bool {
	dec := json.NewDecoder(r.Body)
	if err := dec.Decode(dst); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body: "+err.Error())
		return false
	}
	return true
}

// ifMatch parses the If-Match header. ok is false when the header is absent.
func ifMatch(r *http.Request) (val int, ok bool) {
	raw := r.Header.Get("If-Match")
	if raw == "" {
		return 0, false
	}
	raw = strings.Trim(raw, "\"")
	v, err := strconv.Atoi(raw)
	if err != nil {
		return 0, false
	}
	return v, true
}
