package lib

import (
	"regexp"
	"strconv"
	"strings"

	"lockkit/internal/types"
)

var policyPinRe = regexp.MustCompile(`(?i)For root matrix entry\s+(\w+)\s*,\s*module\s+(\w+)\s+must remain on series\s+([\d.]+)`)

func parsePolicyPins(entryID, policyText string) map[string]string {
	pins := map[string]string{}
	for _, m := range policyPinRe.FindAllStringSubmatch(policyText, -1) {
		if m[1] == entryID {
			pins[m[2]] = m[3]
		}
	}
	return pins
}

func semverLess(a, b string) bool {
	ap := strings.Split(a, ".")
	bp := strings.Split(b, ".")
	n := len(ap)
	if len(bp) > n {
		n = len(bp)
	}
	for i := 0; i < n; i++ {
		var av, bv int
		if i < len(ap) {
			av, _ = strconv.Atoi(ap[i])
		}
		if i < len(bp) {
			bv, _ = strconv.Atoi(bp[i])
		}
		if av != bv {
			return av < bv
		}
	}
	return false
}

func lowestPin(current, candidate string) string {
	if candidate == "" {
		return current
	}
	if current == "" {
		return candidate
	}
	if semverLess(candidate, current) {
		return candidate
	}
	return current
}

func contains(list []string, val string) bool {
	for _, v := range list {
		if v == val {
			return true
		}
	}
	return false
}

func depName(edge string) string {
	parts := strings.SplitN(edge, "@", 2)
	return parts[0]
}

func depVersion(edge string) string {
	parts := strings.SplitN(edge, "@", 2)
	if len(parts) < 2 {
		return ""
	}
	return parts[1]
}

func pickVersion(pkg types.Package, mod, entryID string, policyPins map[string]string, explicitPin string) string {
	if pin, ok := policyPins[mod]; ok && contains(pkg.Versions, pin) {
		return pin
	}
	if explicitPin != "" && contains(pkg.Versions, explicitPin) {
		return explicitPin
	}
	return pkg.Latest
}

func FoldGraphX(catalog types.Catalog, policy types.PolicyCtx, roots types.Roots) types.NodeMap {
	entryID := roots.EntryID
	policyPins := parsePolicyPins(entryID, policy.Text)
	nodes := map[string]types.NodeInfo{}
	stack := append([]string{}, roots.Seeds...)
	seen := map[string]bool{}
	requested := map[string]string{}

	for len(stack) > 0 {
		mod := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		pkg, ok := catalog.Packages[mod]
		if !ok {
			continue
		}
		ver := pickVersion(pkg, mod, entryID, policyPins, requested[mod])
		if seen[mod] {
			if nodes[mod].Version == ver {
				continue
			}
		}
		seen[mod] = true
		rawDeps := pkg.Deps[ver]
		resolved := []string{}
		for _, edge := range rawDeps {
			name := depName(edge)
			pinned := depVersion(edge)
			if pinned != "" {
				prev := requested[name]
				requested[name] = lowestPin(requested[name], pinned)
				if requested[name] != prev && seen[name] {
					delete(seen, name)
					stack = append(stack, name)
				}
				use := requested[name]
				if depPkg, ok := catalog.Packages[name]; ok && use != "" && contains(depPkg.Versions, use) {
					resolved = append(resolved, name+"@"+use)
				} else if pinned != "" {
					resolved = append(resolved, name+"@"+pinned)
				} else {
					resolved = append(resolved, name)
				}
			} else {
				resolved = append(resolved, name)
			}
			if !seen[name] {
				stack = append(stack, name)
			}
		}
		nodes[mod] = types.NodeInfo{Version: ver, Deps: resolved}
	}
	return types.NodeMap{
		EntryID:      entryID,
		StorageClass: roots.StorageClass,
		Nodes:        nodes,
	}
}
