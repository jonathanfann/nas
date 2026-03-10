.PHONY: run format lint install

run:
	.venv/bin/python file_server.py

format:
	.venv/bin/black app/ file_server.py
	.venv/bin/djlint templates/ --reformat
	@if command -v npx >/dev/null 2>&1; then npx eslint static/js/ --fix; fi

lint:
	.venv/bin/black app/ file_server.py --check
	.venv/bin/djlint templates/ --check
	@if command -v npx >/dev/null 2>&1; then npx eslint static/js/; fi

install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
	@if command -v npm >/dev/null 2>&1; then npm install; fi
