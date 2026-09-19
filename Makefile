.PHONY: all lint lint-shell lint-python lint-json lint-yaml validate

PLUGINS := $(wildcard plugins/*)

all: lint

lint: lint-shell lint-python lint-json lint-yaml

lint-shell:
	@echo "== shellcheck =="
	@find plugins -name '*.sh' -print0 | xargs -0 -r shellcheck

lint-python:
	@echo "== ruff check =="
	@ruff check plugins

lint-json:
	@echo "== JSON syntax =="
	@find . \( -path ./.git -o -path ./.serena -o -path '*/node_modules' \) -prune -o -name '*.json' -print0 \
		| xargs -0 -r -n1 sh -c 'jq empty "$$1" || (echo "invalid JSON: $$1" && exit 1)' _

lint-yaml:
	@echo "== yamllint (excludes .serena, which is Serena's own generated config) =="
	@yaml_files=$$(find . \( -path ./.git -o -path ./.serena -o -path '*/node_modules' \) -prune -o \( -name '*.yml' -o -name '*.yaml' \) -print); \
	if [ -z "$$yaml_files" ]; then \
		echo "no YAML files yet - nothing to lint"; \
	else \
		echo "$$yaml_files" | xargs yamllint; \
	fi

validate:
	@for p in $(PLUGINS); do \
		echo "== claude plugin validate $$p =="; \
		claude plugin validate "$$p" || exit 1; \
	done
