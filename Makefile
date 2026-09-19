.PHONY: all lint lint-shell lint-python lint-json lint-yaml validate

PLUGINS := $(wildcard plugins/*)
VENV := .venv
RUFF := $(VENV)/bin/ruff
YAMLLINT := $(VENV)/bin/yamllint

all: lint

lint: lint-shell lint-python lint-json lint-yaml

# Pinned-version venv for ruff/yamllint, so `make lint` gives the same result
# locally and in CI regardless of whatever ruff/yamllint happen to already be
# on PATH. Re-installs only when requirements-dev.txt changes.
$(VENV)/.installed: requirements-dev.txt
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -q -r requirements-dev.txt
	touch $(VENV)/.installed

lint-shell:
	@echo "== shellcheck =="
	@find plugins -name '*.sh' -print0 | xargs -0 -r shellcheck

lint-python: $(VENV)/.installed
	@echo "== ruff check =="
	@$(RUFF) check plugins

lint-json:
	@echo "== JSON syntax =="
	@find . \( -path ./.git -o -path ./.serena -o -path ./$(VENV) -o -path '*/node_modules' \) -prune -o -name '*.json' -print0 \
		| xargs -0 -r -n1 sh -c 'jq empty "$$1" || (echo "invalid JSON: $$1" && exit 1)' _

lint-yaml: $(VENV)/.installed
	@echo "== yamllint (excludes .serena, which is Serena's own generated config) =="
	@yaml_files=$$(find . \( -path ./.git -o -path ./.serena -o -path ./$(VENV) -o -path '*/node_modules' \) -prune -o \( -name '*.yml' -o -name '*.yaml' \) -print); \
	if [ -z "$$yaml_files" ]; then \
		echo "no YAML files yet - nothing to lint"; \
	else \
		echo "$$yaml_files" | xargs $(YAMLLINT); \
	fi

validate:
	@for p in $(PLUGINS); do \
		echo "== claude plugin validate $$p =="; \
		claude plugin validate "$$p" || exit 1; \
	done
