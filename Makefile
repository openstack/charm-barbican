#!/usr/bin/make

clean:
	rm -Rf build

generate: clean
	tox -e generate
