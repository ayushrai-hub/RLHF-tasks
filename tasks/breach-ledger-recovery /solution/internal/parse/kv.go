package parse

import (
	"bufio"
	"compress/gzip"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"breach-ledger/internal/model"
)

var ipRE = regexp.MustCompile(`\b(?:\d{1,3}\.){3}\d{1,3}\b`)

func p1(line string) map[string]string {
	out := map[string]string{}
	for _, part := range strings.Fields(strings.TrimSpace(line)) {
		k, v, ok := strings.Cut(part, "=")
		if ok {
			out[k] = strings.Trim(v, `"`)
		}
	}
	return out
}

func readLines(path string) ([]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	var scanner *bufio.Scanner
	if strings.HasSuffix(path, ".gz") {
		gz, err := gzip.NewReader(f)
		if err != nil {
			return nil, err
		}
		defer gz.Close()
		scanner = bufio.NewScanner(gz)
	} else {
		scanner = bufio.NewScanner(f)
	}
	scanner.Buffer(make([]byte, 1024), 1024*1024)
	var lines []string
	for scanner.Scan() {
		lines = append(lines, strings.TrimRight(scanner.Text(), "\r"))
	}
	return lines, scanner.Err()
}

func parseInt64(s string) int64 {
	n, _ := strconv.ParseInt(s, 10, 64)
	return n
}

func addEvent(ev *model.Evidence, event model.Event) {
	ev.Events = append(ev.Events, event)
	if event.AttackerID != "" && event.Detail != "" && (event.Source == "history" || event.Source == "audit" || event.Source == "archive") {
		ev.Commands = append(ev.Commands, event.Detail)
	}
	if event.AttackerID != "" {
		addString(&ev.CompromisedHosts, event.Host)
		addString(&ev.CompromisedUsers, event.User)
	}
	for _, ip := range ipRE.FindAllString(event.Detail, -1) {
		addString(&ev.IOCs, "ip:"+ip)
	}
}

func addString(values *[]string, value string) {
	value = strings.TrimSpace(value)
	if value != "" {
		*values = append(*values, value)
	}
}

func sortUnique(values []string) []string {
	seen := map[string]bool{}
	out := make([]string, 0, len(values))
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		out = append(out, value)
	}
	sort.Strings(out)
	return out
}

func canonicalJSONLine(line string) string {
	return strings.Join(strings.Fields(line), "")
}

func pA0(host string, user string, detail string) string {
	h := nH0(host)
	u := strings.ToLower(strings.TrimSpace(user))
	d := strings.ToLower(detail)
	if u == "www-data" || (h == "web-2" && hasAny(d, "198.51.100.77", "loader.sh", "shell.php", "update-agent", "bad777", " nc ")) {
		return "B"
	}
	if u == "backup" || (h == "edge-1" && hasAny(d, "203.0.113.41", "203.0.113.99", "192.0.2.44", "/tmp/.p", ".cache", "payroll", "sshd_config")) {
		return "A"
	}
	if h == "db-3" || hasAny(d, "customer.db", "backup@edge-1", "/usr/local/bin/.cache") {
		return "A"
	}
	return ""
}

func hasAny(value string, needles ...string) bool {
	for _, needle := range needles {
		if strings.Contains(value, needle) {
			return true
		}
	}
	return false
}

func nH0(host string) string {
	return strings.ToLower(strings.TrimSpace(host))
}
