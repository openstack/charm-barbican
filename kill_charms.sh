#!/bin/bash

for charm in $1
do
    juju destroy-service ${charm}
done

for charm in $1
do
    while true; do
        JS_OUT=$(juju status ${charm} --format=short | \
                 sed -e 's!^.*new available version.*!!' | grep -vE '^$')
        if [[ -z $JS_OUT ]]; then
            exit 0
        fi
        echo "!$JS_OUT!"
        sleep 3
    done
done
