test:
	python -m pytest

test-verbose:
	python -m pytest -s

test-full:
	RUN_MONEY_TESTS=true python -m pytest -s

test-integration:
	RUN_MONEY_TESTS=true python -m pytest -s -m apitest

couch:
	docker pull couchdb
	docker run -d -p 5984:5984 --name localcouch -e COUCHDB_USER=admin -e COUCHDB_PASSWORD=password couchdb:latest

initcouch: couch
	echo "Sleeping while couch boots"
	sleep 5
	curl -X PUT http://admin:password@localhost:5984/_users
	curl -X PUT http://admin:password@localhost:5984/_replicator
	curl -X PUT http://admin:password@localhost:5984/_global_changes

runcouch:
	docker start localcouch

redis:
	docker pull redis
	docker run --name zeus-redis -p 6379:6379 -d redis