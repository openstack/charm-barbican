# this is just for the reactive handlers and calls into the charm.
from __future__ import absolute_import
from __future__ import print_function

import sys
sys.path.append('src/lib')

import charms.reactive as reactive

print(sys.path)
import os
print(os.getcwd())
print(os.path.dirname(os.path.realpath(__file__)))
# This charm's library contains all of the handler code
import charm.openstack.barbican as barbican


# use a synthetic state to ensure that it get it to be installed independent of
# the install hook.
@reactive.when_not('charm.installed')
def install_packages():
    barbican.install()
    reactive.set_state('charm.installed')


@reactive.when('amqp.connected')
def setup_amqp_req(amqp):
    barbican.setup_amqp_req(amqp)


@reactive.when('shared-db.connected')
def setup_database(database):
    barbican.setup_database(database)


@reactive.when('identity-service.connected')
def setup_endpoint(keystone):
    barbican.setup_endpoint(keystone)


@reactive.when('shared-db.available')
@reactive.when('identity-service.available')
@reactive.when('amqp.available')
def render_stuff(*args):
    barbican.render_configs(args)
