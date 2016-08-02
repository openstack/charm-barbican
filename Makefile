#!/usr/bin/make
LAYER_PATH := layers

clean:
	rm -Rf build .tox .testrepository

build: clean
	LAYER_PATH=$(LAYER_PATH) tox -e build
