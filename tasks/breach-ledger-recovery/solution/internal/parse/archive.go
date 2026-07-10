package parse

import (
	"archive/zip"
	"bytes"
	"compress/gzip"
	"encoding/json"
	"io"
	"path/filepath"
	"sort"
	"strings"

	"breach-ledger/internal/model"
	"breach-ledger/internal/normalize"
)

type archiveExfil struct {
	DestinationIP string   `json:"destination_ip"`
	Protocol      string   `json:"protocol"`
	Bytes         int64    `json:"bytes"`
	Timestamp     string   `json:"timestamp"`
	Files         []string `json:"files"`
}

func unitK(dir string, ev *model.Evidence, issues *[]model.Issue) {
	files, _ := filepath.Glob(filepath.Join(dir, "*.zip"))
	sort.Strings(files)
	for _, file := range files {
		reader, err := zip.OpenReader(file)
		if err != nil {
			continue
		}
		for _, member := range reader.File {
			ev.Summary["archive_entries"]++
			if !normalize.NP2(member.Name) {
				model.AddIssue(issues, "archive_escape", "unsafe archive member")
				continue
			}
			rc, err := member.Open()
			if err != nil {
				continue
			}
			data, _ := io.ReadAll(rc)
			rc.Close()
			switch member.Name {
			case "manifest/exfil.json":
				var ex archiveExfil
				if json.Unmarshal(data, &ex) == nil {
					if ex.Bytes >= ev.Exfiltration.Bytes {
						ev.Exfiltration = model.Exfiltration{DestinationIP: ex.DestinationIP, Protocol: ex.Protocol, Bytes: ex.Bytes, Timestamp: ex.Timestamp}
					}
					addString(&ev.IOCs, "ip:"+ex.DestinationIP)
					for _, p := range ex.Files {
						if normalize.NP1(p) {
							addString(&ev.StolenFiles, p)
						} else {
							model.AddIssue(issues, "path_traversal", "unsafe exfil path")
						}
					}
				}
			case "nested/commands.log.gz":
				gz, err := gzip.NewReader(bytes.NewReader(data))
				if err != nil {
					continue
				}
				cmdData, _ := io.ReadAll(gz)
				gz.Close()
				for i, line := range strings.Split(strings.TrimSpace(string(cmdData)), "\n") {
					parts := strings.SplitN(line, " ", 4)
					if len(parts) != 4 {
						continue
					}
					cmd := normalize.NT1(parts[3])
					addEvent(ev, model.Event{Seq: 8100 + int64(i), TS: parts[0], Host: normalize.NT3(parts[1]), User: normalize.NT2(parts[2]), Source: "archive", Action: "archive_command", Detail: cmd, AttackerID: "A"})
				}
			}
		}
		reader.Close()
	}
}
