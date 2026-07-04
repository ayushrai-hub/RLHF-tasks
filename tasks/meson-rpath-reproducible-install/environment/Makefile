SHELL := /bin/bash

.PHONY: smoke package replay reconcile clean inspect

smoke:
	bash scripts/pipeline.sh smoke

package:
	bash scripts/pipeline.sh fresh

replay:
	bash scripts/pipeline.sh resume

reconcile:
	bash scripts/pipeline.sh reconcile

inspect:
	bash scripts/pipeline.sh inspect

clean:
	rm -rf /app/work/capsule /app/output
