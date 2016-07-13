#!/usr/bin/make
LAYER_PATH := layers

clean:
	rm -Rf build .tox .testrepository

build: clean
	LAYER_PATH=$(LAYER_PATH) tox -e build

lint:
	@tox -e pep8

test:
	@echo Starting unit tests...
	@tox -e py34,py35
