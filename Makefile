#
# Makefile
#

MODULE = kodicontroller

# Install packages from requirements file
.PHONY: init
init:
	pip install -r requirements.txt

# Clean build and dist directories
.PHONY: clean
clean:
	rm -rf build
	rm -rf dist

# Build source and wheel distributions
.PHONY: build
build:
	python setup.py sdist
	python setup.py bdist_wheel

# Upload using twine
.PHONY: upload
upload:
	twine upload dist/*

# Execute tests in a clean virtual environment
.PHONY: runtest
runtest:
	echo "VIRTUAL ENVIRONMENT SETUP:"; \
	virtualenv --clear testenv; \
	source ./testenv/bin/activate; \
	pip install -e .; \
	cd tests; \
	echo "\nRUNNING TEST SUITE:"; \
	python -m unittest -v test_${MODULE}; \
	cd ../; \
	deactivate; \
	rm -rf testenv; \
