// Starter skeleton - replace with your cdn-pop-coassigner optimizer.
package main

import "os"

func main() {
	outDir := "output_data"
	if len(os.Args) >= 3 {
		outDir = os.Args[2]
	}
	_ = os.WriteFile(outDir+"/assignment.jsonl", []byte(""), 0644)
}
