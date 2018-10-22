import amulet

import barbicanclient.client as barbican_client
import keystoneclient.exceptions

from charmhelpers.contrib.openstack.amulet.deployment import (
    OpenStackAmuletDeployment
)

from charmhelpers.contrib.openstack.amulet.utils import (
    OpenStackAmuletUtils,
    DEBUG,
)

# Use DEBUG to turn on debug logging
u = OpenStackAmuletUtils(DEBUG)


class BarbicanBasicDeployment(OpenStackAmuletDeployment):
    """Amulet tests on a basic Barbican deployment."""

    def __init__(self, series, openstack=None, source=None, stable=False):
        """Deploy the entire test environment.
        """
        super(BarbicanBasicDeployment, self).__init__(
            series, openstack, source, stable)
        self._add_services()
        self._add_relations()
        self._configure_services()
        self._deploy()

        u.log.info('Waiting on extended status checks...')
        exclude_services = []
        self._auto_wait_for_status(exclude_services=exclude_services)

        self.d.sentry.wait()
        self._initialize_tests()

    def _add_services(self):
        """Add services

           Add the services that we're testing, where barbican is local,
           and the rest of the service are from lp branches that are
           compatible with the local charm (e.g. stable or next).
           """
        this_service = {'name': 'barbican'}
        other_services = [
            {'name': 'percona-cluster', 'constraints': {'mem': '3072M'}},
            {'name': 'rabbitmq-server'},
            {'name': 'keystone'}
        ]
        super(BarbicanBasicDeployment, self)._add_services(
            this_service, other_services)

    def _add_relations(self):
        """Add all of the relations for the services."""
        relations = {
            'barbican:shared-db': 'percona-cluster:shared-db',
            'barbican:amqp': 'rabbitmq-server:amqp',
            'barbican:identity-service': 'keystone:identity-service',
            'keystone:shared-db': 'percona-cluster:shared-db',
        }
        super(BarbicanBasicDeployment, self)._add_relations(relations)

    def _configure_services(self):
        """Configure all of the services."""
        keystone_config = {
            'admin-password': 'openstack',
            'admin-token': 'ubuntutesting',
        }
        # say we don't need an HSM for these tests
        barbican_config = {
            'require-hsm-plugin': False,
        }
        pxc_config = {
            'dataset-size': '25%',
            'max-connections': 1000,
            'root-password': 'ChangeMe123',
            'sst-password': 'ChangeMe123',
        }
        configs = {
            'keystone': keystone_config,
            'barbican': barbican_config,
            'percona-cluster': pxc_config,
        }
        super(BarbicanBasicDeployment, self)._configure_services(configs)

    def _initialize_tests(self):
        """Perform final initialization before tests get run."""
        # Access the sentries for inspecting service units
        self.barbican_sentry = self.d.sentry['barbican'][0]
        self.pxc_sentry = self.d.sentry['percona-cluster'][0]
        self.keystone_sentry = self.d.sentry['keystone'][0]
        self.rabbitmq_sentry = self.d.sentry['rabbitmq-server'][0]
        u.log.debug('openstack release val: {}'.format(
            self._get_openstack_release()))
        u.log.debug('openstack release str: {}'.format(
            self._get_openstack_release_string()))

        # Authenticate admin with keystone
        self.keystone_session, self.keystone = u.get_default_keystone_session(
            self.keystone_sentry,
            openstack_release=self._get_openstack_release(),
            api_version=3)

    def test_100_services(self):
        """Verify the expected services are running on the corresponding
           service units."""
        u.log.debug('Checking system services on units...')

        barbican_svcs = [
            'apache2', 'barbican-worker',
        ]

        service_names = {
            self.barbican_sentry: barbican_svcs,
        }

        ret = u.validate_services_by_name(service_names)
        if ret:
            amulet.raise_status(amulet.FAIL, msg=ret)

        u.log.debug('OK')

    def test_110_service_catalog(self):
        """Verify that the service catalog endpoint data is valid."""
        u.log.debug('Checking keystone service catalog data...')

        actual = self.keystone.service_catalog.get_endpoints()

        # v3 endpoint check
        endpoint_check = [
            {
                'id': u.not_null,
                'interface': interface,
                'region': 'RegionOne',
                'region_id': 'RegionOne',
                'url': u.valid_url,
            }
            for interface in ('admin', 'public', 'internal')]
        validate_catalog = u.validate_v3_svc_catalog_endpoint_data

        expected = {
            'key-manager': endpoint_check,
            'identity': endpoint_check,
        }

        ret = validate_catalog(expected, actual)
        if ret:
            amulet.raise_status(amulet.FAIL, msg=ret)

        u.log.debug('OK')

    def test_114_barbican_api_endpoint(self):
        """Verify the barbican api endpoint data."""
        u.log.debug('Checking barbican api endpoint data...')
        endpoints = self.keystone.endpoints.list()
        u.log.debug(endpoints)
        admin_port = '9312'
        internal_port = public_port = '9311'
        # For keystone v3 it's slightly different.
        expected = {'id': u.not_null,
                    'region': 'RegionOne',
                    'region_id': 'RegionOne',
                    'url': u.valid_url,
                    'interface': u.not_null,  # we match this in the test
                    'service_id': u.not_null}

        ret = u.validate_v3_endpoint_data(
            endpoints, admin_port, internal_port, public_port, expected)

        if ret:
            message = 'barbican endpoint: {}'.format(ret)
            amulet.raise_status(amulet.FAIL, msg=message)

        u.log.debug('OK')

    def test_200_barbican_identity_relation(self):
        """Verify the barbican to keystone identity-service relation data"""
        u.log.debug('Checking barbican to keystone identity-service '
                    'relation data...')
        unit = self.barbican_sentry
        relation = ['identity-service', 'keystone:identity-service']
        barbican_ip = unit.relation(*relation)['private-address']
        barbican_admin_endpoint = "http://%s:9312" % (barbican_ip)
        barbican_endpoint = "http://%s:9311" % (barbican_ip)

        expected = {
            'admin_url': barbican_admin_endpoint,
            'internal_url': barbican_endpoint,
            'private-address': barbican_ip,
            'public_url': barbican_endpoint,
            'region': 'RegionOne',
            'service': 'barbican',
        }

        ret = u.validate_relation_data(unit, relation, expected)
        if ret:
            message = u.relation_error('barbican identity-service', ret)
            amulet.raise_status(amulet.FAIL, msg=message)

        u.log.debug('OK')

    def test_201_keystone_barbican_identity_relation(self):
        """Verify the keystone to barbican identity-service relation data"""
        u.log.debug('Checking keystone:barbican identity relation data...')
        unit = self.keystone_sentry
        relation = ['identity-service', 'barbican:identity-service']
        id_relation = unit.relation(*relation)
        id_ip = id_relation['private-address']
        expected = {
            'admin_token': 'ubuntutesting',
            'auth_host': id_ip,
            'auth_port': "35357",
            'auth_protocol': 'http',
            'private-address': id_ip,
            'service_host': id_ip,
            'service_password': u.not_null,
            'service_port': "5000",
            'service_protocol': 'http',
            'service_tenant': 'services',
            'service_tenant_id': u.not_null,
            'service_username': 'barbican',
        }
        ret = u.validate_relation_data(unit, relation, expected)
        if ret:
            message = u.relation_error('keystone identity-service', ret)
            amulet.raise_status(amulet.FAIL, msg=message)

        u.log.debug('OK')

    def test_203_barbican_amqp_relation(self):
        """Verify the barbican to rabbitmq-server amqp relation data"""
        u.log.debug('Checking barbican:rabbitmq amqp relation data...')
        unit = self.barbican_sentry
        relation = ['amqp', 'rabbitmq-server:amqp']
        expected = {
            'username': 'barbican',
            'private-address': u.valid_ip,
            'vhost': 'openstack'
        }

        ret = u.validate_relation_data(unit, relation, expected)
        if ret:
            message = u.relation_error('barbican amqp', ret)
            amulet.raise_status(amulet.FAIL, msg=message)

        u.log.debug('OK')

    def test_204_barbican_amqp_relation(self):
        """Verify the rabbitmq-server to barbican amqp relation data"""
        u.log.debug('Checking rabbitmq:barbican barbican relation data...')
        unit = self.rabbitmq_sentry
        relation = ['amqp', 'barbican:amqp']
        expected = {
            'hostname': u.valid_ip,
            'private-address': u.valid_ip,
            'password': u.not_null,
        }

        ret = u.validate_relation_data(unit, relation, expected)
        if ret:
            message = u.relation_error('rabbitmq barbican', ret)
            amulet.raise_status(amulet.FAIL, msg=message)

        u.log.debug('OK')

    @staticmethod
    def _find_or_create(items, key, create):
        """Find or create the thing in the items

        :param items: the items to search using the key
        :param key: a function that key(item) -> boolean if found.
        :param create: a function to call if the key() never was true.
        :returns: the item that was either found or created.
        """
        for i in items:
            if key(i):
                return i
        return create()

    def test_400_api_connection(self):
        """Simple api calls to check service is up and responding"""
        u.log.debug('Checking api functionality...')

        # This handles both keystone v2 and v3.
        # For keystone v2 we need a user:
        #  - 'demo' user
        #  - has a project 'demo'
        #  - in the 'demo' project
        #  - with an 'admin' role
        # For keystone v3 we need a user:
        #  - 'default' domain
        #  - 'demo' user
        #  - 'demo' project
        #  - 'admin' role -- to be able to delete.

        # barbican requires a user with creator or admin role on the project
        # when creating a secret (which this test does).  Therefore, we create
        # a demo user, demo project, and then get a demo barbican client and do
        # the secret.  ensure that the default domain is created.

        # find or create the 'default' domain
        domain = self._find_or_create(
            items=self.keystone.domains.list(),
            key=lambda u: u.name == 'default',
            create=lambda: self.keystone.domains.create(
                "default",
                description="domain for barbican testing",
                enabled=True))
        # find or create the 'demo' user
        demo_user = self._find_or_create(
            items=self.keystone.users.list(domain=domain.id),
            key=lambda u: u.name == 'demo',
            create=lambda: self.keystone.users.create(
                'demo',
                domain=domain.id,
                description="Demo user for barbican tests",
                enabled=True,
                email="demo@example.com",
                password="pass"))
        # find or create the 'demo' project
        demo_project = self._find_or_create(
            items=self.keystone.projects.list(domain=domain.id),
            key=lambda x: x.name == 'demo',
            create=lambda: self.keystone.projects.create(
                'demo',
                domain=domain.id,
                description='barbican testing project',
                enabled=True))
        # create the role for the user - needs to be admin so that the
        # secret can be deleted - note there is only one admin role, and it
        # should already be created - if not, then this will fail later.
        admin_role = self._find_or_create(
            items=self.keystone.roles.list(),
            key=lambda r: r.name.lower() == 'admin',
            create=lambda: None)
        # now grant the creator role to the demo user.
        try:
            self.keystone.roles.check(
                role=admin_role,
                user=demo_user,
                project=demo_project)
        except keystoneclient.exceptions.NotFound:
            # create it if it isn't found
            self.keystone.roles.grant(
                role=admin_role,
                user=demo_user,
                project=demo_project)
        keystone_ip = self.keystone_sentry.info['public-address']
        self.keystone_demo = u.authenticate_keystone(
            keystone_ip, demo_user.name, 'pass', api_version=3,
            user_domain_name=domain.name,
            project_domain_name=domain.name,
            project_name=demo_project.name)

        # Authenticate admin with barbican endpoint
        barbican_ep = self.keystone.service_catalog.url_for(
            service_type='key-manager', interface='publicURL')
        barbican = barbican_client.Client(session=self.keystone_demo.session,
                                          endpoint=barbican_ep)
        # now create the secret.
        my_secret = barbican.secrets.create()
        my_secret.name = u'Random plain text password'
        my_secret.payload = u'password'
        my_secret_ref = my_secret.store()
        assert(my_secret_ref is not None)
        # and now delete the secret
        my_secret.delete()
        u.log.debug('OK')

    def test_900_restart_on_config_change(self):
        """Verify that the specified services are restarted when the config
           is changed.
        """
        sentry = self.barbican_sentry
        juju_service = 'barbican'

        # Expected default and alternate values
        set_default = {'debug': 'False'}
        set_alternate = {'debug': 'True'}

        # Services which are expected to restart upon config change,
        # and corresponding config files affected by the change
        conf_file = '/etc/barbican/barbican.conf'
        services = {
            'barbican-worker': conf_file,
        }

        # Make config change, check for service restarts
        u.log.debug('Making config change on {}...'.format(juju_service))
        mtime = u.get_sentry_time(sentry)
        self.d.configure(juju_service, set_alternate)

        sleep_time = 40
        for s, conf_file in services.iteritems():
            u.log.debug("Checking that service restarted: {}".format(s))
            if not u.validate_service_config_changed(sentry, mtime, s,
                                                     conf_file,
                                                     retry_count=4,
                                                     retry_sleep_time=20,
                                                     sleep_time=sleep_time):
                self.d.configure(juju_service, set_default)
                msg = "service {} didn't restart after config change".format(s)
                amulet.raise_status(amulet.FAIL, msg=msg)
            sleep_time = 0

        self.d.configure(juju_service, set_default)
        u.log.debug('OK')

    def _assert_services(self, should_run):
        services = ('barbican-worker', )
        u.get_unit_process_ids(
            {self.barbican_sentry: services},
            expect_success=should_run)

    def test_910_pause_and_resume(self):
        """The services can be paused and resumed. """
        self._assert_services(should_run=True)
        action_id = u.run_action(self.barbican_sentry, "pause")
        assert u.wait_on_action(action_id), "Pause action failed."

        self._assert_services(should_run=False)

        action_id = u.run_action(self.barbican_sentry, "resume")
        assert u.wait_on_action(action_id), "Resume action failed"
        self._assert_services(should_run=True)
        u.log.debug('OK')
