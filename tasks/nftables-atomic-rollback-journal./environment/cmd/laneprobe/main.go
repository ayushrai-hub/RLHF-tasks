package main

import (
	"encoding/json"
	"fmt"
	"os"

	"nfrd.local/nfrd/tools"
)

func main() {
	profile := "yard"
	if len(os.Args) > 1 {
		profile = os.Args[1]
	}
	out := tools.LaneProbe(profile)
	data, _ := json.Marshal(out)
	fmt.Println(string(data))
}
