venv:
	python3 -m venv .venv

shell:
	@echo "Run: source .venv/bin/activate"

install: venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -r requirements.txt

list:
	.venv/bin/python -m pip list

format:
	ruff format .

uninstall:
	.venv/bin/python -m pip uninstall $(pkg)

uv:
	uv venv .venv
