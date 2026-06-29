package store

import (
	"crypto/rand"
	"encoding/hex"
	"errors"
	"sync"
)

var (
	ErrConflict = errors.New("handle already enrolled")
	ErrMissing  = errors.New("account not found")
)

type Account struct {
	ID              string
	Handle          string
	SecretRaw       []byte
	SigningMaterial []byte
}

type AccountStore struct {
	mu       sync.Mutex
	byID     map[string]*Account
	byHandle map[string]string
}

func NewAccountStore() *AccountStore {
	return &AccountStore{
		byID:     make(map[string]*Account),
		byHandle: make(map[string]string),
	}
}

func (s *AccountStore) Enroll(handle string, secretRaw []byte) (*Account, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, ok := s.byHandle[handle]; ok {
		return nil, ErrConflict
	}
	id, err := randomID()
	if err != nil {
		return nil, err
	}
	signing, err := randomBytes(32)
	if err != nil {
		return nil, err
	}
	secretCopy := make([]byte, len(secretRaw))
	copy(secretCopy, secretRaw)
	signCopy := make([]byte, len(signing))
	copy(signCopy, signing)
	acct := &Account{
		ID:              id,
		Handle:          handle,
		SecretRaw:       secretCopy,
		SigningMaterial: signCopy,
	}
	s.byID[id] = acct
	s.byHandle[handle] = id
	return acct, nil
}

func (s *AccountStore) Rebind(handle string, secretRaw []byte) (*Account, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	id, ok := s.byHandle[handle]
	if !ok {
		return nil, ErrMissing
	}
	signing, err := randomBytes(32)
	if err != nil {
		return nil, err
	}
	secretCopy := make([]byte, len(secretRaw))
	copy(secretCopy, secretRaw)
	signCopy := make([]byte, len(signing))
	copy(signCopy, signing)
	acct := &Account{
		ID:              id,
		Handle:          handle,
		SecretRaw:       secretCopy,
		SigningMaterial: signCopy,
	}
	s.byID[id] = acct
	return acct, nil
}

func (s *AccountStore) RotateSigning(id string) (*Account, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	acct, ok := s.byID[id]
	if !ok {
		return nil, ErrMissing
	}
	signing, err := randomBytes(32)
	if err != nil {
		return nil, err
	}
	signCopy := make([]byte, len(signing))
	copy(signCopy, signing)
	rotated := &Account{
		ID:              acct.ID,
		Handle:          acct.Handle,
		SecretRaw:       acct.SecretRaw,
		SigningMaterial: signCopy,
	}
	s.byID[id] = rotated
	return rotated, nil
}

func (s *AccountStore) GetByID(id string) (*Account, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	acct, ok := s.byID[id]
	if !ok {
		return nil, ErrMissing
	}
	return acct, nil
}

func randomID() (string, error) {
	buf := make([]byte, 16)
	if _, err := rand.Read(buf); err != nil {
		return "", err
	}
	return hex.EncodeToString(buf), nil
}

func randomBytes(n int) ([]byte, error) {
	buf := make([]byte, n)
	if _, err := rand.Read(buf); err != nil {
		return nil, err
	}
	return buf, nil
}
