.PHONY: clean clean-build clean-pyc clean-test develop help install lint lint/flake8 lint/black uninstall
.DEFAULT_GOAL := install

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

lint/black: ## check style with black
	black --check embykeeper

lint/flake8: ## check style with flake8
	flake8 embykeeper

lint: lint/black lint/flake8 ## check style

develop: clean ## install the package at current location, keeping it editable
	pip install -e .

install: clean ## install the package to the active Python's site-packages
	pip install .

