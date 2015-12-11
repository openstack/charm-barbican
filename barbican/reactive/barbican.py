from openstack.adapters import OpenStackRelationAdapters
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
    pass


def api_port(service):
    return API_PORTS[service]


@hook('install')
def install_packages():
    status_set('maintenance', 'Installing packages')
    add_source("ppa:gnuoy/barbican-alt")
    configure_installation_source(config('openstack-origin'))
    apt_update()
    apt_install(filter_installed_packages(PACKAGES))


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

    CONFIGS = 'bob'
    public_url = '{}:{}'.format(canonical_url(CONFIGS, PUBLIC),
                                api_port('barbican-public-api'))
    admin_url = '{}:{}'.format(canonical_url(CONFIGS, ADMIN),
                               api_port('barbican-admin-api'))
    internal_url = '{}:{}'.format(canonical_url(CONFIGS, INTERNAL),
                                  api_port('barbican-internal-api')
                                  )
    keystone.register_endpoints('keystore', config('region'), public_url,
                                internal_url, admin_url)

@when('shared-db.available')
@when('identity-service.available')
@when('amqp.available')
def render_stuff(*args):
    adapters = BarbicanAdapters(args)
    #release = os_release('barbican-common')
    release = os_release('python-keystonemiddleware')
    for conf in [BARBICAN_ADMIN_PASTE_CONF, BARBICAN_API_CONF,
                 BARBICAN_API_PASTE_CONF]:
        render(source=conf,
               template_loader=get_loader('templates/', release),
               target='{}/{}'.format(BARBICAN_DIR, conf),
               context=adapters)
