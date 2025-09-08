venv:
	python3 -m venv .venv

shell:
	@echo "Run: source .venv/bin/activate"

install:
	.venv/bin/pip3 install -r requirements.txt

list:
	.venv/bin/pip3 list

uninstall:
	.venv/bin/pip3 uninstall $(pkg)

uv:
	uv venv .venv
