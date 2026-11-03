.PHONY: check-node setup-venv setup-tests setup-docs build clean-build docs-clean package docs-fetch docs-sync docs-build docs test unit-test modinput-test run help

APP_NAME := $$(cat globalConfig.json | jq -r '.meta.name')
APP_VERSION := $$(cat package/app.manifest | jq -r '.info.id.version')

PYTHON_PATH := $(shell which python3.9 || pyenv which python3.9 2>/dev/null || which python3)
VENV_COMMAND := $(PYTHON_PATH) -m venv

VENV := .venv
UCC_GEN := $(VENV)/bin/ucc-gen

# Repo that contains the Docusaurus site
DOCS_SITE_REPO ?= git@github.com:splunk-platform-apps/.github.git
# Branch, tag or commit SHA
DOCS_SITE_REF  ?= main
# Folder inside that repo that contains package.json
DOCS_SITE_SUBDIR ?= documentation/boilerplate
# Local, git-ignored working copy
DOCS_SITE_DIR  ?= .docs-site
# local overrides (docusaurus.config.ts)
DOCS_LOCAL_DIR ?= website
# Markdown sources in this repo
DOCS_CONTENT   ?= $(CURDIR)/docs
NPM       ?= npm
DOCS_HOST ?= localhost
DOCS_PORT ?= 3000
# Where package.json lives after checkout
DOCS_SITE_PATH := $(DOCS_SITE_DIR)/$(DOCS_SITE_SUBDIR)

OUTPUT_PATH := output
OUTPUT_BUILD_PATH := $(OUTPUT_PATH)/$(APP_NAME)

SPLUNK_HOST ?= localhost
SPLUNK_HEC_TOKEN ?= 00000000-0000-0000-0000-000000000000
SPLUNK_USER ?= admin
SPLUNK_PASSWORD ?= Chang3d!

MODINPUT_TEST_PREPARE ?= true
RUN_PREPARE ?= true

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

help:
	@cat $(MAKEFILE_LIST) | python3 -c "$$PRINT_HELP_PYSCRIPT"

check-node:
	@command -v node >/dev/null 2>&1 || { echo "Node.js is required (>= 18). Install it first."; exit 1; }
	@command -v $(NPM) >/dev/null 2>&1 || { echo "$(NPM) not found."; exit 1; }

# ── Docs Retrieval ──────────────────────────

docs-fetch: ## Fetch only standard configuration files
	@mkdir -p $(DOCS_SITE_DIR)
	@if [ ! -d $(DOCS_SITE_DIR)/.git ]; then \
		git -C $(DOCS_SITE_DIR) init -q && \
		git -C $(DOCS_SITE_DIR) remote add origin $(DOCS_SITE_REPO); \
	else \
		git -C $(DOCS_SITE_DIR) remote set-url origin $(DOCS_SITE_REPO); \
	fi
	git -C $(DOCS_SITE_DIR) sparse-checkout set $(DOCS_SITE_SUBDIR)
	git -C $(DOCS_SITE_DIR) fetch --depth 1 origin $(DOCS_SITE_REF)
	git -C $(DOCS_SITE_DIR) checkout --force FETCH_HEAD
	@test -f $(DOCS_SITE_PATH)/package.json || \
		{ echo "package.json not found in $(DOCS_SITE_PATH). Check DOCS_SITE_SUBDIR."; exit 1; }

docs-sync: docs-fetch ## Copy local site files (docusaurus.config.ts, ...) into the site folder
	cp -R $(DOCS_LOCAL_DIR)/. $(DOCS_SITE_PATH)/
	cp -R $(DOCS_CONTENT)/. $(DOCS_SITE_PATH)/docs

# ── Environment Setup ──────────────────────────

setup-venv: ## Create Python virtual environment
	$(VENV_COMMAND) $(VENV)
	. $(VENV)/bin/activate && pip install --upgrade splunk-add-on-ucc-framework

setup-tests: ## Setup tests virtual environment
	$(VENV_COMMAND) $(VENV)
	. $(VENV)/bin/activate && pip install -r tests/test-requirements.txt

# Run npm only when package.json or the lockfile changes
setup-docs: check-node docs-sync ## Install Docusaurus dependencies
	@cd $(DOCS_SITE_PATH) && \
	if [ -f package-lock.json ]; then lock=package-lock.json; else lock=package.json; fi; \
	hash=$$(cksum$$lock); \
	if [ ! -d node_modules ] || [ "$$hash" != "$$(cat node_modules/.lock-hash 2>/dev/null)" ]; then \
		if [ -f package-lock.json ]; then $(NPM) ci; else $(NPM) install; fi && \
		echo "$$hash" > node_modules/.lock-hash; \
	else \
		echo "Docs dependencies up to date."; \
	fi

# ── Build ──────────────────────────

build: setup-venv ## Build with UCC
	$(UCC_GEN) build --ta-version=$(APP_VERSION);

package: build ## Build and package with UCC
	mkdir -p dist
	$(UCC_GEN) package --path $(OUTPUT_BUILD_PATH) -o dist

docs-build: etup-docs ## Build static site into .docs-site
	cd $(DOCS_SITE_PATH) && DOCS_PATH=$(DOCS_CONTENT) npx docusaurus build

docs: docs-build ## Build docs with mkdocs
	cd $(DOCS_SITE_PATH) && npx docusaurus serve --host $(DOCS_HOST) --port $(DOCS_PORT)

# ── Clean ──────────────────────────

clean-build: ## Remove build artifacts
	rm -rf $(OUTPUT_BUILD_PATH)

docs-clean: ## Remove the fetched site, dependencies and build output
	rm -rf $(DOCS_SITE_DIR)

# ── Docker Development ─────────────────────────

run: ## Run add-on in docker container
	$(RUN_PREPARE)
	@if [ -f "docker-compose.yml" ]; then \
		( \
			export SPLUNK_APP_ID=$(APP_NAME); \
			export SPLUNK_APP_PACKAGE=$(OUTPUT_BUILD_PATH); \
			export SPLUNK_HEC_TOKEN=$(SPLUNK_HEC_TOKEN); \
			export SPLUNK_USER=$(SPLUNK_USER); \
			export SPLUNK_PASSWORD=$(SPLUNK_PASSWORD); \
			docker compose up -d; \
			echo "Waiting for Splunk to be ready..."; \
			until docker compose logs splunk 2>&1 | grep -q "Ansible playbook complete"; do sleep 1; printf "."; done; \
			echo " SPLUNK READY"; \
		); \
	else \
		echo "Skipping: docker-compose.yml file not found"; \
	fi

# ── Tests ─────────────────────────

test: unit-test ## Run default test suite (unit tests)

unit-test: setup-tests ## Run unit tests
	@if [ -d "tests/unit" ]; then \
		( . $(VENV)/bin/activate; pytest -v tests/unit ); \
	else \
		echo "Skipping: tests/unit directory not found"; \
	fi

modinput-test: setup-tests ## Run modinput functional tests
	$(MODINPUT_TEST_PREPARE)
	@if [ -d "tests/modinput_functional" ]; then \
		( . $(VENV)/bin/activate; \
		pytest -vvv -n 1 \
			--splunk-type=external \
			--splunk-hec-token="$(SPLUNK_HEC_TOKEN)" \
			--splunk-user=$(SPLUNK_USER) \
			--splunk-password=$(SPLUNK_PASSWORD) \
			--password=$(SPLUNK_PASSWORD) \
			--splunk-web-scheme=https \
			--splunk-host=$(SPLUNK_HOST) \
			tests/modinput_functional ); \
	else \
		echo "Skipping: tests/modinput_functional directory not found"; \
	fi
