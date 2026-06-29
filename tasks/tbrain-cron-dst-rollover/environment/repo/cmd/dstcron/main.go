package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"

	"dstcron/internal/schedule"
	"dstcron/internal/zone"
)

// dstcron computes, for each query, the next UTC second at which a daily
// wall-clock schedule next fires under a local time zone whose offset changes at
// two explicitly given transition instants.
//
// Usage:
//
//	dstcron <inputfile>
//
// The input file uses one directive per line:
//
//	offset_std   <minutes>   standard offset, minutes east of UTC
//	offset_dst   <minutes>   daylight offset, minutes east of UTC
//	spring_forward <utcsec>  UTC second the clock jumps forward (std -> dst)
//	fall_back      <utcsec>  UTC second the clock falls back (dst -> std)
//	fire_at      <HH:MM>     daily wall-clock fire time
//	next         <utcsec>    a query instant (may repeat)
//
// For each `next` query, in input order, the program prints on its own line the
// UTC second of the next time the local clock reads the `fire_at` time of day.
func main() {
	if len(os.Args) != 2 {
		fmt.Fprintln(os.Stderr, "usage: dstcron <inputfile>")
		os.Exit(2)
	}
	f, err := os.Open(os.Args[1])
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	defer f.Close()

	var (
		z          zone.Zone
		haveStd    bool
		haveDst    bool
		haveSpring bool
		haveFall   bool
		target     int64 = -1
		queries    []int64
	)

	scanner := bufio.NewScanner(f)
	scanner.Buffer(make([]byte, 0, 1024*1024), 16*1024*1024)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		fields := strings.Fields(line)
		switch fields[0] {
		case "offset_std":
			z.OffsetStd = mustInt(fields, 1)
			haveStd = true
		case "offset_dst":
			z.OffsetDst = mustInt(fields, 1)
			haveDst = true
		case "spring_forward":
			z.Spring = mustInt64(fields, 1)
			haveSpring = true
		case "fall_back":
			z.Fall = mustInt64(fields, 1)
			haveFall = true
		case "fire_at":
			target = mustTimeOfDay(fields, 1)
		case "next":
			queries = append(queries, mustInt64(fields, 1))
		default:
			fmt.Fprintf(os.Stderr, "unknown directive %q\n", fields[0])
			os.Exit(1)
		}
	}
	if err := scanner.Err(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if !haveStd || !haveDst || !haveSpring || !haveFall {
		fmt.Fprintln(os.Stderr, "missing offset or transition directive")
		os.Exit(1)
	}
	if target < 0 {
		fmt.Fprintln(os.Stderr, "missing fire_at directive")
		os.Exit(1)
	}

	var b strings.Builder
	for _, q := range queries {
		fmt.Fprintf(&b, "%d\n", schedule.NextFire(z, q, target))
	}
	fmt.Print(b.String())
}

func mustInt(fields []string, i int) int {
	if i >= len(fields) {
		fmt.Fprintf(os.Stderr, "directive %q missing value\n", fields[0])
		os.Exit(1)
	}
	v, err := strconv.Atoi(fields[i])
	if err != nil {
		fmt.Fprintf(os.Stderr, "bad integer %q\n", fields[i])
		os.Exit(1)
	}
	return v
}

func mustInt64(fields []string, i int) int64 {
	return int64(mustInt(fields, i))
}

func mustTimeOfDay(fields []string, i int) int64 {
	if i >= len(fields) {
		fmt.Fprintf(os.Stderr, "directive %q missing value\n", fields[0])
		os.Exit(1)
	}
	parts := strings.Split(fields[i], ":")
	if len(parts) != 2 {
		fmt.Fprintf(os.Stderr, "bad time-of-day %q\n", fields[i])
		os.Exit(1)
	}
	hh, err1 := strconv.Atoi(parts[0])
	mm, err2 := strconv.Atoi(parts[1])
	if err1 != nil || err2 != nil || hh < 0 || hh > 23 || mm < 0 || mm > 59 {
		fmt.Fprintf(os.Stderr, "bad time-of-day %q\n", fields[i])
		os.Exit(1)
	}
	return int64(hh)*3600 + int64(mm)*60
}
