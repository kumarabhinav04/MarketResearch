.PHONY: install dev test lint seed run serve clean-demo

install:
	python3 -m pip install -e .

dev:
	python3 -m pip install -e ".[dev]"

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

lint:
	python3 -m compileall -q src tests

seed:
	PYTHONPATH=src python3 -m aifactory.cli seed-demo

run:
	PYTHONPATH=src python3 -m aifactory.cli run --as-of-date 2026-09-01 --generate-report

serve:
	uvicorn aifactory.api:app --app-dir src --host 0.0.0.0 --port 8000 --reload

clean-demo:
	PYTHONPATH=src python3 -m aifactory.cli reset-demo

