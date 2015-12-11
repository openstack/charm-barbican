from openstack.adapters import OpenStackRelationAdapters, ConfigurationAdapter
from openstack.ip import canonical_url, PUBLIC, INTERNAL, ADMIN
from charmhelpers.contrib.openstack.utils import (
    configure_installation_source,
)
from charmhelpers.fetch import (
    apt_install,
    add_source,
    apt_update,
    filter_installed_packages,
)
from charms.reactive import (
    hook,
    remove_state,
    set_state,
    when,
    when_not,
)
from charmhelpers.core.hookenv import config
from charmhelpers.core.hookenv import status_set
from charmhelpers.core.templating import render
from charmhelpers.core.hookenv import unit_private_ip
from charmhelpers.contrib.openstack.templating import get_loader
from charmhelpers.contrib.openstack.utils import os_release
from charmhelpers.core.host import restart_on_change

API_PORTS = {
    'barbican-api': 9311,
    'barbican-public-api': 9311,
    'barbican-admin-api': 9312,
    'barbican-internal-api': 9313,
}
PACKAGES = ['barbican-common', 'barbican-api', 'barbican-worker',
            'python-mysqldb']
BARBICAN_DIR = '/etc/barbican'
BARBICAN_ADMIN_PASTE_CONF = "barbican-admin-paste.ini"
BARBICAN_API_CONF = "barbican-api.conf"
BARBICAN_API_PASTE_CONF = "barbican-api-paste.ini"


class BarbicanAdapters(OpenStackRelationAdapters):
    """
    Adapters class for the Barbican charm.
    """
    def __init__(self, relations):
        super(BarbicanAdapters, self).__init__(relations, options=BarbicanConfigurationAdapter)


class BarbicanConfigurationAdapter(ConfigurationAdapter):

    def __init__(self):
        super(BarbicanConfigurationAdapter, self).__init__()
        if config('keystone-api-version') not in ['2', '3', 'none']:
            raise ValueError('Unsupported keystone-api-version (%s). Should'
                             'be 2 or 3' % (config('keystone-api-version')))
        
    @property
    def barbican_api_keystone_pipeline(self):
        if config('keystone-api-version') == "2":
            return 'keystone_authtoken context apiapp'
        else:
            return 'keystone_v3_authtoken context apiapp'

    @property
    def barbican_api_pipeline(self):
        if config('keystone-api-version') == "2":
            return "keystone_authtoken context apiapp"
        elif config('keystone-api-version') == "3":
            return "keystone_v3_authtoken context apiapp"
        elif config('keystone-api-version') == "none":
            return "unauthenticated-context apiapp"


class OpenStackCharm(object):

    packages = []
    """Packages to install"""

    api_ports = {}
    """
    Dictionary mapping services to ports for public, admin and
    internal endpoints
    """

    service_type = None
    """Keystone endpoint type"""

    default_service = None
    """Default service for the charm"""

    def __init__(self):
        self.config = config()

    def install(self):
        """
        Install packages related to this charm based on
        contents of packages attribute.
        """
        packages = filter_installed_packages(self.packages)
        if packages:
            status_set('maintenance', 'Installing packages')
            apt_install(packages, fatal=True)

    def api_port(self, service, endpoint_type=PUBLIC):
        """
        Determine the API port for a particular endpoint type
        """
        return self.api_ports[service][endpoint_type]

    def configure_source(self):
        """Configure installation source"""
        configure_installation_source(self.config['openstack-origin'])
        apt_update(fatal=True)

    @property
    def region(self):
        """OpenStack Region"""
        return self.config['region']

    @property
    def public_url(self):
        """Public Endpoint URL"""
        return "{}:{}".format(canonical_url(PUBLIC),
                              self.api_port(self.default_service,
                                            PUBLIC))
    @property
    def admin_url(self):
        """Admin Endpoint URL"""
        return "{}:{}".format(canonical_url(ADMIN),
                              self.api_port(self.default_service,
                                            ADMIN))
    @property
    def internal_url(self):
        """Internal Endpoint URL"""
        return "{}:{}".format(canonical_url(INTERNAL),
                              self.api_port(self.default_service,
                                            INTERNAL))


class BarbicanCharm(OpenStackCharm):

    packages =  [
        'barbican-common',
        'barbican-api',
        'barbican-worker',
        'python-mysqldb'
    ]

    api_ports = {
        'barbican-api': {
            PUBLIC: 9311,
            ADMIN: 9312,
            INTERNAL: 9313,
        }
    }

    service_type = 'secretstore'
    default_service = 'barbican-api'


class OpenStackCharmFactory(object):

    releases = {}
    """
    Dictionary mapping OpenStack releases to their associated
    Charm class for this charm
    """

    first_release = "icehouse"
    """
    First OpenStack release which this factory supports Charms for
    """

    @classmethod
    def charm(cls, release=None):
        """Get the right charm for the configured OpenStack series"""
        if release and release in cls.releases:
            return cls.release[release]
        else:
            return cls.release[cls.first_release]


class BarbicanCharmFactory(OpenStackCharmFactory):

    releases = {
        'liberty': BarbicanCharm
    }

    first_release = 'liberty'


@hook('install')
def install_packages():
    charm = BarbicanCharmFactory.charm()
    add_source("ppa:gnuoy/barbican-alt")
    charm.configure_source()
    charm.install()


@when('amqp.connected')
def setup_amqp_req(amqp):
    amqp.request_access(username=config('rabbit-user'),
                        vhost=config('rabbit-vhost'))


@when('shared-db.connected')
def setup_database(database):
    database.configure(config('database'), config('database-user'),
                       unit_private_ip())


@when('identity-service.connected')
def setup_endpoint(keystone):
    charm = BarbicanCharmFactory.charm()
    keystone.register_endpoints(charm.service_type,
                                charm.region,
                                charm.public_url,
                                charm.internal_url,
                                charm.admin_url)

@when('shared-db.available')
@when('identity-service.available')
@when('amqp.available')
@restart_on_change({
    '/etc/barbican/barbican*': [ 'barbican-api', 'barbican-worker' ]
})
def render_stuff(*args):
    charm = BarbicanCharmFactory.charm()
    adapters = BarbicanAdapters(args)
    #release = os_release('barbican-common')
    release = os_release('python-keystonemiddleware')
    for conf in [BARBICAN_ADMIN_PASTE_CONF, BARBICAN_API_CONF,
                 BARBICAN_API_PASTE_CONF]:
        render(source=conf,
               template_loader=get_loader('templates/', release),
               target='{}/{}'.format(BARBICAN_DIR, conf),
               context=adapters)
