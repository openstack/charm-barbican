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

import charmhelpers.contrib.openstack.utils as ch_utils
import charmhelpers.core.hookenv as hookenv
import charmhelpers.core.unitdata as unitdata
import charmhelpers.fetch

import charms_openstack.charm
import charms_openstack.adapters
import charms_openstack.ip as os_ip

PACKAGES = ['barbican-common', 'barbican-api', 'barbican-worker',
            'python-mysqldb']
BARBICAN_DIR = '/etc/barbican/'
BARBICAN_CONF = BARBICAN_DIR + "barbican.conf"
BARBICAN_API_PASTE_CONF = BARBICAN_DIR + "barbican-api-paste.ini"

OPENSTACK_RELEASE_KEY = 'barbican-charm.openstack-release-version'


###
# Handler functions for events that are interesting to the Barbican charms

def install():
    """Use the singleton from the BarbicanCharm to install the packages on the
    unit
    """
    unitdata.kv().unset(OPENSTACK_RELEASE_KEY)
    BarbicanCharm.singleton.install()


def setup_endpoint(keystone):
    """When the keystone interface connects, register this unit in the keystone
    catalogue.

    :param keystone: instance of KeystoneRequires() class from i/f
    """
    charm = BarbicanCharm.singleton
    keystone.register_endpoints(charm.service_type,
                                charm.region,
                                charm.public_url,
                                charm.internal_url,
                                charm.admin_url)


def render_configs(interfaces_list):
    """Using a list of interfaces, render the configs and, if they have
    changes, restart the services on the unit.

    :param interfaces_list: [RelationBase] interfaces from reactive
    """
    BarbicanCharm.singleton.render_with_interfaces(interfaces_list)


def generate_mkek(hsm):
    """Ask barbican to generate an MKEK in the backend store using the HSM.
    This assumes that an HSM is available, and configured.  Uses the charm.
    """
    BarbicanCharm.singleton.action_generate_mkek(hsm)


def generate_hmac(hsm):
    """Ask barbican to generate an HMAC in the backend store using the HSM.
    This assumes that an HSM is available, and configured.  Uses the charm.
    """
    BarbicanCharm.singleton.action_generate_hmac(hsm)


def assess_status():
    """Just call the BarbicanCharm.singleton.assess_status() command to update
    status on the unit.
    """
    BarbicanCharm.singleton.assess_status()


###
# Implementation of the Barbican Charm classes

class BarbicanConfigurationAdapter(
        charms_openstack.adapters.ConfigurationAdapter):

    def __init__(self):
        super(BarbicanConfigurationAdapter, self).__init__()
        if self.keystone_api_version not in ['2', '3', 'none']:
            raise ValueError(
                "Unsupported keystone-api-version ({}). It should be 2 or 3"
                .format(self.keystone_api_version))

    @property
    def barbican_api_keystone_pipeline(self):
        if self.keystone_api_version == "2":
            return 'cors keystone_authtoken context apiapp'
        else:
            return 'cors keystone_v3_authtoken context apiapp'

    @property
    def barbican_api_pipeline(self):
        return {
            "2": "cors keystone_authtoken context apiapp",
            "3": "cors keystone_v3_authtoken context apiapp",
            "none": "cors unauthenticated-context apiapp"
        }[self.keystone_api_version]

    @property
    def barbican_api_keystone_audit_pipeline(self):
        if self.keystone_api_version == "2":
            return 'keystone_authtoken context audit apiapp'
        else:
            return 'keystone_v3_authtoken context audit apiapp'


class HSMAdapter(charms_openstack.adapters.OpenStackRelationAdapter):
    """Adapt the barbican-hsm-plugin relation for use in rendering the config
    for Barbican.  Note that the HSM relation is optional, so we have a class
    variable 'exists' that we can test in the template to see if we should
    render HSM parameters into the template.
    """

    interface_type = 'hsm'

    @property
    def library_path(self):
        """Provide a library_path property to the template if it exists"""
        try:
            return self.relation.plugin_data['library_path']
        except:
            return ''

    @property
    def login(self):
        """Provide a login property to the template if it exists"""
        try:
            return self.relation.plugin_data['login']
        except:
            return ''

    @property
    def slot_id(self):
        """Provide a slot_id property to the template if it exists"""
        try:
            return self.relation.plugin_data['slot_id']
        except:
            return ''


class BarbicanAdapters(charms_openstack.adapters.OpenStackAPIRelationAdapters):
    """
    Adapters class for the Barbican charm.

    This plumbs in the BarbicanConfigurationAdapter as the ConfigurationAdapter
    to provide additional properties.
    """

    relation_adapters = {
        'hsm': HSMAdapter,
    }

    def __init__(self, relations):
        super(BarbicanAdapters, self).__init__(
            relations, options_instance=BarbicanConfigurationAdapter())


class BarbicanCharm(charms_openstack.charm.OpenStackCharm):
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
    }

    adapters_class = BarbicanAdapters

    def install(self):
        """Customise the installation, configure the source and then call the
        parent install() method to install the packages
        """
        # DEBUG - until seed random change lands into xenial cloud archive
        # BUG #1599550 - barbican + softhsm2 + libssl1.0.0:
        #  pkcs11:_generate_random() fails
        # WARNING: This charm can't be released into stable until the bug is
        # fixed.
        charmhelpers.fetch.add_source("ppa:ajkavanagh/barbican")
        self.configure_source()
        # and do the actual install
        super(BarbicanCharm, self).install()

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


# Determine the charm class by the supported release
@charms_openstack.charm.register_os_release_selector
def select_release():
    """Determine the release based on the python-keystonemiddleware that is
    installed.

    Note that this function caches the release after the first install so that
    it doesn't need to keep going and getting it from the package information.
    """
    release_version = unitdata.kv().get(OPENSTACK_RELEASE_KEY, None)
    if release_version is None:
        release_version = ch_utils.os_release('python-keystonemiddleware')
        unitdata.kv().set(OPENSTACK_RELEASE_KEY, release_version)
    return release_version
