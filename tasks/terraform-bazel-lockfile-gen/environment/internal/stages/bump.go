package stages

import statelib "lockkit/mkstate/lib"

func Bump(entry string) {
	statelib.TouchEpoch(entry)
	statelib.TouchReplayGen()
}
