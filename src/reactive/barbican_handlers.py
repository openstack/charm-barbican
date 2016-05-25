# this is just for the reactive handlers and calls into the charm.
from __future__ import absolute_import

import charms.reactive as reactive
import charmhelpers.core.hookenv as hookenv

# This charm's library contains all of the handler code associated with
# barbican
import charm.openstack.barbican as barbican


# use a synthetic state to ensure that it get it to be installed independent of
# the install hook.
@reactive.when_not('charm.installed')
def install_packages():
    barbican.install()
    reactive.set_state('charm.installed')


@reactive.when('amqp.connected')
def setup_amqp_req(amqp):
    """Use the amqp interface to request access to the amqp broker using our
    local configuration.
    """
    amqp.request_access(username=hookenv.config('rabbit-user'),
                        vhost=hookenv.config('rabbit-vhost'))


@reactive.when('shared-db.connected')
def setup_database(database):
    """On receiving database credentials, configure the database on the
    interface.
    """
    database.configure(hookenv.config('database'),
                       hookenv.config('database-user'),
                       hookenv.unit_private_ip())


@reactive.when('identity-service.connected')
def setup_endpoint(keystone):
    barbican.setup_endpoint(keystone)


@reactive.when('shared-db.available')
@reactive.when('identity-service.available')
@reactive.when('amqp.available')
def render_stuff(*args):
    barbican.render_configs(args)
