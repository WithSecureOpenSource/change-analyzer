VENV_DIR := .venv
PYTHON := ${VENV_DIR}/bin/python

venv: $(VENV_DIR)/bin/activate
$(VENV_DIR)/bin/activate: setup.py
	test -d $(VENV_DIR) || python3 -m venv $(VENV_DIR)

install: venv
	$(PYTHON) -m pip install --upgrade pip setuptools
	$(PYTHON) -m pip install -e .[dev]

clean:
	rm -rf $(VENV_DIR)
	rm -rf change_analyzer.egg-info

publish: install
	. $(VENV_DIR)/bin/activate; $(VENV_DIR)/bin/semantic-release publish \
		-D version_variable=change_analyzer/__init__.py:__version__ \
		-D upload_to_release=true \
		-D upload_to_pypi=false \
		--verbosity=DEBUG

print-version: install
	. $(VENV_DIR)/bin/activate; \
	$(VENV_DIR)/bin/semantic-release print-version \
		-D version_variable=change_analyzer/__init__.py:__version__
