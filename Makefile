.PHONY: lint
lint:
	flake8

.PHONY: type-check
type-check:
	mypy .

.PHONY: test
test:
	pytest .

.PHONY: integration-test
integration-test:
ifndef ALERTDB_TEST_GCP_PROJECT
	$(error "ALERTDB_TEST_GCP_PROJECT environment variable must be set for integration tests")
endif

.PHONY: precommit
precommit: lint type-check test

.PHONY: premerge
premerge: precommit integration-test
