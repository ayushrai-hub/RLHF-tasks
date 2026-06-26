package isolation

import "fmt"

// Banner prints a cosmetic heal marker (no effect on votes).
func Banner(epoch int) string {
	return fmt.Sprintf("heal-marker-%d", epoch)
}
