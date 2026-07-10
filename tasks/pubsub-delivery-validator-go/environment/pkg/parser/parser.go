package parser

import (
	"encoding/json"
	"fmt"
	"os"
)

type DeliveryLog struct {
	Subscriptions    []Subscription   `json:"subscriptions"`
	Deliveries       []Delivery       `json:"deliveries"`
	DeadLetterConfig DeadLetterConfig `json:"deadletter_config"`
}

type Subscription struct {
	ClientID    string `json:"client_id"`
	Topic       string `json:"topic"`
	SubscribeTS int64  `json:"subscribe_ts"`
	UnsubTS     int64  `json:"unsub_ts"`
	Priority    int    `json:"priority"`
}

type Delivery struct {
	DeliveryID string `json:"delivery_id"`
	MsgID      string `json:"msg_id"`
	Topic      string `json:"topic"`
	ClientID   string `json:"client_id"`
	SeqNum     int    `json:"seq_num"`
	Timestamp  int64  `json:"timestamp"`
	Acked      bool   `json:"acked"`
	Priority   int    `json:"priority"`
	RetryCount int    `json:"retry_count"`
}

type DeadLetterConfig struct {
	MaxRetryCount     int   `json:"max_retry_count"`
	TTLMs             int64 `json:"ttl_ms"`
	PriorityThreshold int   `json:"priority_threshold"`
}

func LoadDeliveryLog(path string) DeliveryLog {
	data, err := os.ReadFile(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Cannot read log: %v\n", err)
		os.Exit(1)
	}
	var log DeliveryLog
	if err := json.Unmarshal(data, &log); err != nil {
		fmt.Fprintf(os.Stderr, "Cannot parse log: %v\n", err)
		os.Exit(1)
	}
	return log
}
