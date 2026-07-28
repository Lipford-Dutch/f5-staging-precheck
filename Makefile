# check_multi 2.0 – developer tasks
# Run `make help` for a list of targets.

SHELL := bash
.DEFAULT_GOAL := help

.PHONY: help lint syntax test check smoke report clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

lint: ## Run ShellCheck across all shell scripts
	./scripts/shellcheck_all.sh

syntax: ## Bash syntax check (no execution)
	@find . -name '*.sh' -not -path './results/*' -not -path './.git/*' -print0 \
		| xargs -0 -n1 bash -n
	@bash -n bin/check_multi
	@echo "Syntax OK"

test: ## Run the bats unit tests
	./tests/run_tests.sh

smoke: ## Dry-run every check module against the example inventory
	@set -euo pipefail; \
	for c in preflight platform umm certs keys syncgroup network; do \
		echo ">> dry-run $$c"; \
		./bin/check_multi --dry-run $$c examples/devices.txt >/dev/null; \
	done; \
	echo "Smoke OK"

check: lint syntax test smoke ## Run the full local verification suite

clean: ## Remove generated results
	rm -rf results
	@echo "Cleaned"
