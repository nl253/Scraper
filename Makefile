# variables
VENV_DIR = ./venv
PIP = $(VENV_DIR)/bin/pip3
PYTHON = $(VENV_DIR)/bin/python3

# rules
virtualenv-init:
	python -m venv ./venv

docs:
	sphinx

verify:
	echo $(VENV_DIR)
	echo $(PIP)

activate:
	. $(VENV_DIR)/bin/activate

requirements:
	$(PIP) install -r ./requirements.txt

requirements-dev:
	$(PIP) install -r ./requirements/dev.txt

requirements-docs:
	$(PIP) install -r ./requirements/docs.txt

requirements-tests:
	$(PIP) install -r ./requirements/tests.txt
