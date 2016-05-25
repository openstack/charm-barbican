# The barbican handlers class

# bare functions are provided to the reactive handlers to perform the functions
# needed on the class.
from __future__ import absolute_import

import charmhelpers.fetch
import charmhelpers.contrib.openstack.utils as ch_utils

import charms_openstack.charm
import charms_openstack.adapters
import charms_openstack.ip as os_ip

PACKAGES = ['barbican-common', 'barbican-api', 'barbican-worker',
            'python-mysqldb']
BARBICAN_DIR = '/etc/barbican'
BARBICAN_ADMIN_PASTE_CONF = "barbican-admin-paste.ini"
BARBICAN_API_CONF = "barbican-api.conf"
BARBICAN_API_PASTE_CONF = "barbican-api-paste.ini"


###
# Handler functions for events that are interesting to the Barbican charms

def install():
    """Use the singleton from the BarbicanCharm to install the packages on the
    unit
    """
    BarbicanCharm.singleton.install()


def setup_endpoint(keystone):
    """When the keystone interface connects, register this unit in the keystone
    catalogue.
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
    """
    BarbicanCharm.singleton.render_with_interfaces(interfaces_list)


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
            return 'keystone_authtoken context apiapp'
        else:
            return 'keystone_v3_authtoken context apiapp'

    @property
    def barbican_api_pipeline(self):
        return {
            "2": "keystone_authtoken context apiapp",
            "3": "keystone_v3_authtoken context apiapp",
            "none": "unauthenticated-context apiapp"
        }[self.keystone_api_version]


class BarbicanAdapters(charms_openstack.adapters.OpenStackRelationAdapters):
    """
    Adapters class for the Barbican charm.

    This plumbs in the BarbicanConfigurationAdapter as the ConfigurationAdapter
    to provide additional properties.
    """
    def __init__(self, relations):
        super(BarbicanAdapters, self).__init__(
            relations, options=BarbicanConfigurationAdapter)


class BarbicanCharm(charms_openstack.charm.OpenStackCharm):
    """BarbicanCharm provides the specialisation of the OpenStackCharm
    functionality to manage a barbican unit.
    """

    release = 'liberty'
    name = 'barbican'
    packages = PACKAGES
    api_ports = {
        'barbican-api': {
            os_ip.PUBLIC: 9311,
            os_ip.ADMIN: 9312,
            os_ip.INTERNAL: 9313,
        }
    }
    service_type = 'barbican'
    default_service = 'barbican-api'
    services = ['barbican-api', 'barbican-worker']

    restart_map = {
        "{}/{}".format(BARBICAN_DIR, BARBICAN_API_CONF): services,
        "{}/{}".format(BARBICAN_DIR, BARBICAN_ADMIN_PASTE_CONF): services,
        "{}/{}".format(BARBICAN_DIR, BARBICAN_API_PASTE_CONF): services,
    }

    adapters_class = BarbicanAdapters

    def __init__(self, release=None, **kwargs):
        """Custom initialiser for class

        If no release is passed, then the charm determines the release from the
        ch_utils.os_release() function.
        """
        if release is None:
            # release = ch_utils.os_release('barbican-common')
            release = ch_utils.os_release('python-keystonemiddleware')
        super(BarbicanCharm, self).__init__(release=release, **kwargs)

    def install(self):
        """Customise the installation, configure the source and then call the
        parent install() method to install the packages
        """
        charmhelpers.fetch.add_source("ppa:gnuoy/barbican-alt")
        self.configure_source()
        # and do the actual install
        super(BarbicanCharm, self).install()
