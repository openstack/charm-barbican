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
# The barbican handlers class

# bare functions are provided to the reactive handlers to perform the functions
# needed on the class.
from __future__ import absolute_import

import subprocess

import charmhelpers.core.hookenv as hookenv

import charms_openstack.charm
import charms_openstack.adapters
import charms_openstack.ip as os_ip

PACKAGES = ['barbican-common', 'barbican-api', 'barbican-worker',
            'python-mysqldb']
BARBICAN_DIR = '/etc/barbican/'
BARBICAN_CONF = BARBICAN_DIR + "barbican.conf"
BARBICAN_API_PASTE_CONF = BARBICAN_DIR + "barbican-api-paste.ini"
BARBICAN_WSGI_CONF = '/etc/apache2/conf-available/barbican-api.conf'

OPENSTACK_RELEASE_KEY = 'barbican-charm.openstack-release-version'


# select the default release function
charms_openstack.charm.use_defaults('charm.default-select-release')


###
# Implementation of the Barbican Charm classes

# Add some properties to the configuration for templates/code to use with the
# charm instance.  The config_validator is called when the configuration is
# loaded, and the properties are to add those names to the config object.

@charms_openstack.adapters.config_property
def validate_keystone_api_version(config):
    if config.keystone_api_version not in ['2', '3', 'none']:
        raise ValueError(
            "Unsupported keystone-api-version ({}). It should be 2 or 3"
            .format(config.keystone_api_version))


@charms_openstack.adapters.config_property
def barbican_api_keystone_pipeline(config):
    if config.keystone_api_version == "2":
        return 'cors keystone_authtoken context apiapp'
    else:
        return 'cors keystone_v3_authtoken context apiapp'


@charms_openstack.adapters.config_property
def barbican_api_pipeline(config):
    return {
        "2": "cors keystone_authtoken context apiapp",
        "3": "cors keystone_v3_authtoken context apiapp",
        "none": "cors unauthenticated-context apiapp"
    }[config.keystone_api_version]


@charms_openstack.adapters.config_property
def barbican_api_keystone_audit_pipeline(config):
    if config.keystone_api_version == "2":
        return 'keystone_authtoken context audit apiapp'
    else:
        return 'keystone_v3_authtoken context audit apiapp'


# Adapt the barbican-hsm-plugin relation for use in rendering the config
# for Barbican.  Note that the HSM relation is optional, so we have a class
# variable 'exists' that we can test in the template to see if we should
# render HSM parameters into the template.

@charms_openstack.adapters.adapter_property('hsm')
def library_path(hsm):
    """Provide a library_path property to the template if it exists"""
    try:
        return hsm.relation.plugin_data['library_path']
    except:
        return ''


@charms_openstack.adapters.adapter_property('hsm')
def login(hsm):
    """Provide a login property to the template if it exists"""
    try:
        return hsm.relation.plugin_data['login']
    except:
        return ''


@charms_openstack.adapters.adapter_property('hsm')
def slot_id(hsm):
    """Provide a slot_id property to the template if it exists"""
    try:
        return hsm.relation.plugin_data['slot_id']
    except:
        return ''


class BarbicanCharm(charms_openstack.charm.HAOpenStackCharm):
    """BarbicanCharm provides the specialisation of the OpenStackCharm
    functionality to manage a barbican unit.
    """

    release = 'mitaka'
    name = 'barbican'
    packages = PACKAGES
    api_ports = {
        'barbican-worker': {
            os_ip.PUBLIC: 9311,
            os_ip.ADMIN: 9312,
            os_ip.INTERNAL: 9311,
        }
    }
    service_type = 'barbican'
    default_service = 'barbican-worker'
    services = ['apache2', 'barbican-worker']

    # Note that the hsm interface is optional - defined in config.yaml
    required_relations = ['shared-db', 'amqp', 'identity-service']

    restart_map = {
        BARBICAN_CONF: services,
        BARBICAN_API_PASTE_CONF: services,
        BARBICAN_WSGI_CONF: services,
    }

    ha_resources = ['vips', 'haproxy']

    def get_amqp_credentials(self):
        """Provide the default amqp username and vhost as a tuple.

        :returns (username, host): two strings to send to the amqp provider.
        """
        return (self.config['rabbit-user'], self.config['rabbit-vhost'])

    def get_database_setup(self):
        """Provide the default database credentials as a list of 3-tuples

        returns a structure of:
        [
            {'database': <database>,
             'username': <username>,
             'hostname': <hostname of this unit>
             'prefix': <the optional prefix for the database>, },
        ]

        :returns [{'database': ...}, ...]: credentials for multiple databases
        """
        return [
            dict(
                database=self.config['database'],
                username=self.config['database-user'], )
        ]

    def action_generate_mkek(self, hsm):
        """Generate an MKEK on a connected HSM.  Requires that an HSM is
        avaiable via the barbican-hsm-plugin interface, generically known as
        'hsm'.

        Uses the barbican-manage command.

        :param hsm: instance of BarbicanRequires() class from the
                    barbican-hsm-plugin interface
        """
        plugin_data = hsm.plugin_data
        cmd = [
            'barbican-manage', 'hsm', 'gen_mkek',
            '--library-path', plugin_data['library_path'],
            '--passphrase', plugin_data['login'],
            '--slot-id', plugin_data['slot_id'],
            '--length', str(hookenv.config('mkek-key-length')),
            '--label', hookenv.config('label-mkek'),
        ]
        try:
            subprocess.check_call(cmd)
            hookenv.log("barbican-mangage hsm gen_mkek succeeded")
        except subprocess.CalledProcessError:
            str_err = "barbican-manage hsm gen_mkek failed."
            hookenv.log(str_err)
            raise Exception(str_err)

    def action_generate_hmac(self, hsm):
        """Generate an HMAC on a connected HSM.  Requires that an HSM is
        avaiable via the barbican-hsm-plugin interface, generically known as
        'hsm'.

        Uses the barbican-manage command.

        :param hsm: instance of BarbicanRequires() class from the
                    barbican-hsm-plugin interface
        """
        plugin_data = hsm.plugin_data
        cmd = [
            'barbican-manage', 'hsm', 'gen_hmac',
            '--library-path', plugin_data['library_path'],
            '--passphrase', plugin_data['login'],
            '--slot-id', plugin_data['slot_id'],
            '--length', str(hookenv.config('hmac-key-length')),
            '--label', hookenv.config('label-hmac'),
        ]
        try:
            subprocess.check_call(cmd)
            hookenv.log("barbican-mangage hsm gen_hmac succeeded")
        except subprocess.CalledProcessError:
            str_err = "barbican-manage hsm gen_hmac failed."
            hookenv.log(str_err)
            raise Exception(str_err)

    def states_to_check(self, required_relations=None):
        """Override the default states_to_check() for the assess_status
        functionality so that, if we have to have an HSM relation, then enforce
        it on the assess_status() call.

        If param required_relations is not None then it overrides the
        instance/class variable self.required_relations.

        :param required_relations: [list of state names]
        :returns: [states{} as per parent method]
        """
        if required_relations is None:
            required_relations = self.required_relations
        if hookenv.config('require-hsm-plugin'):
            required_relations.append('hsm')
        return super(BarbicanCharm, self).states_to_check(
            required_relations=required_relations)
