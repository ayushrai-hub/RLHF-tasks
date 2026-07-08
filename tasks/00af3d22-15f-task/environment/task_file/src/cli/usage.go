package cli

import (
	"fmt"
	"io"
)

func usage(w io.Writer) {
	fmt.Fprintln(w, "tabsettle - build a settlement plan for a shared-tab ledger")
	fmt.Fprintln(w, "")
	fmt.Fprintln(w, "usage: tabsettle [-participants FILE] [-rules FILE] [-out FILE]")
	fmt.Fprintln(w, "")
	fmt.Fprintln(w, "  -participants FILE  ledger of participants and net balances")
	fmt.Fprintln(w, "  -rules FILE         hard limits (max transfer size)")
	fmt.Fprintln(w, "  -out FILE           where to write the resulting plan.json")
}
