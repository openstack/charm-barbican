# Copyright 2016 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
    barbican.assess_status()


@reactive.when('shared-db.connected')
def setup_database(database):
    """On receiving database credentials, configure the database on the
    interface.
    """
    database.configure(hookenv.config('database'),
                       hookenv.config('database-user'),
                       hookenv.unit_private_ip())
    barbican.assess_status()


@reactive.when('identity-service.connected')
def setup_endpoint(keystone):
    barbican.setup_endpoint(keystone)
    barbican.assess_status()


@reactive.when('shared-db.available')
@reactive.when('identity-service.available')
@reactive.when('amqp.available')
def render_stuff(*args):
    """Render the configuration for Barbican when all the interfaces are
    available.

    Note that the HSM interface is optional (hence the @when_any) and thus is
    only used if it is available.
    """
    # Get the optional hsm relation, if it is available for rendering.
    hsm = reactive.RelationBase.from_state('hsm.available')
    if hsm is not None:
        args = args + (hsm, )
    barbican.render_configs(args)
    barbican.assess_status()


@reactive.when('config.changed')
def config_changed():
    """When the configuration changes, assess the unit's status to update any
    juju state required"""
    barbican.assess_status()


@reactive.when('identity-service.available')
def configure_ssl(keystone):
    '''Configure SSL access to Barbican if requested'''
    barbican.configure_ssl(keystone)
