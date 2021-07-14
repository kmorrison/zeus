test:
	pytest

test-verbose:
	pytest -s

test-full:
	RUN_MONEY_TESTS=true pytest -s

test-integration:
	RUN_MONEY_TESTS=true pytest -s -m apitest