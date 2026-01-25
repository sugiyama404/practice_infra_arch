venv:
	python3 -m venv .venv

shell:
	@echo "Run: source .venv/bin/activate"

install: venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -r requirements_local.txt

list:
	.venv/bin/python -m pip list

uninstall:
	.venv/bin/python -m pip uninstall $(pkg)

format:
	ruff format .

uv:
	uv venv .venv
