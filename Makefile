.PHONY: test check aggregate

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

check:
	python3 -m compileall -q src scripts
	@for script in scripts/*.sh; do bash -n "$$script"; done
	python3 -m json.tool protocol/benchmark-v1.json >/dev/null
	python3 -m json.tool schemas/result.schema.json >/dev/null
	PYTHONPATH=src python3 -m unittest discover -s tests -v

aggregate:
	./scripts/aggregate.sh
