#!/usr/bin/make
LAYER_PATH := layers

clean:
	rm -Rf build .tox .testrepository

generate: clean
	LAYER_PATH=$(LAYER_PATH) tox -e generate

lint:
	@tox -e lint

test:
	@echo Starting unit tests...
	@tox -e py27
