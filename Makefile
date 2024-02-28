.DEFAULT_GOAL := all
sources = src/message_flow_rabbitmq tests

.PHONY: .pdm  ## Check that PDM is installed
.pdm:
	@pdm -V || echo 'Please install PDM: https://pdm.fming.dev/latest/#installation'

.PHONY: install  ## Install the package, dependencies, and pre-commit for local development
install: .pdm
	pdm info
	pdm install --group :all

.PHONY: refresh-lockfiles  ## Sync lockfiles with requirements files.
refresh-lockfiles: .pdm
	pdm update --update-reuse --group :all

.PHONY: rebuild-lockfiles  ## Rebuild lockfiles from scratch, updating all dependencies
rebuild-lockfiles: .pdm
	pdm update --update-eager --group :all

.PHONY: format  ## Auto-format python source files
format: .pdm
	pdm run ruff --fix $(sources)
	pdm run ruff format $(sources)

.PHONY: lint  ## Lint python source files
lint: .pdm
	pdm run ruff $(sources)
	pdm run ruff format --check $(sources)

.PHONY: codespell  ## Use Codespell to do spellchecking
codespell: .pdm
	pdm run codespell

.PHONY: typecheck  ## Perform type-checking
typecheck: .pdm
	pdm run pyright $(sources)

.PHONY: test  ## Run all tests, skipping the type-checker integration tests
test: .pdm
	pdm run coverage run -m pytest --durations=10

.PHONY: testcov  ## Run tests and generate a coverage report, skipping the type-checker integration tests
testcov: test
	@echo "building coverage html"
	@pdm run coverage html
	@echo "building coverage lcov"
	@pdm run coverage lcov

.PHONY: all  ## Run the standard set of checks performed in CI
all: lint typecheck codespell

.PHONY: clean  ## Clear local caches and build artifacts
clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]'`
	rm -f `find . -type f -name '*~'`
	rm -f `find . -type f -name '.*~'`
	rm -rf .cache
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf *.egg-info
	rm -f .coverage
	rm -f .coverage.*
	rm -rf build
	rm -rf dist
	rm -rf site
	rm -rf docs/_build
	rm -rf docs/.changelog.md docs/.version.md docs/.tmp_schema_mappings.html
	rm -rf coverage.xml

.PHONY: help  ## Display this message
help:
	@grep -E \
		'^.PHONY: .*?## .*$$' $(MAKEFILE_LIST) | \
		sort | \
		awk 'BEGIN {FS = ".PHONY: |## "}; {printf "\033[36m%-19s\033[0m %s\n", $$2, $$3}'


.PHONY: start_rabbitmq
start_rabbitmq:
	docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3.12-management

.PHONY: stop_rabbitmq
stop_rabbitmq:
	docker rm -f rabbitmq

.PHONY: consume
consume: .pdm
	pdm run python -m message_flow_rabbitmq consume


.PHONY: produce
produce: .pdm
	pdm run python -m message_flow_rabbitmq produce
