.PHONY: test run-server run-cli lint

test:
	python -m pytest -q

run-server:
	python -m core.server

run-cli:
	python -m core.cli chat --text "hello from vrav"

lint:
	python -m compileall -q core tests
