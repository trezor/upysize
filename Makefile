.PHONY: check style code_check style_check test

check: style_check code_check

style_check:
	@echo [ISORT]
	@isort --check-only .
	@echo [BLACK]
	@black --check .

style:
	@echo [ISORT]
	@isort .
	@echo [BLACK]
	@black .

code_check:
	@echo [MYPY]
	@mypy src
	@echo [FLAKE8]
	@flake8 src

test:
	pytest --cov=.  --cov-report term-missing .
