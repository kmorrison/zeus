test:
	python -m pytest

test-verbose:
	python -m pytest -s

test-full:
	RUN_MONEY_TESTS=true python -m pytest -s

test-integration:
	RUN_MONEY_TESTS=true python -m pytest -s -m apitest