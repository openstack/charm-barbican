#!/usr/bin/make
LAYER_PATH := layers

clean:
	rm -Rf build .tox .testrepository

build: clean
	LAYER_PATH=$(LAYER_PATH) tox -e build

lint:
	@tox -e lint

test:
	@echo Starting unit tests...
	@tox -e py27,py34,py35
