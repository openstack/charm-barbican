#!/usr/bin/python
from keystoneclient.auth import identity
from keystoneclient import session
from barbicanclient import client
import subprocess

keystone_ip = subprocess.check_output(['juju-deployer', '-f', 'keystone']).rstrip()
barbican_ip = subprocess.check_output(['juju-deployer', '-f', 'barbican']).rstrip() 
auth = identity.v3.Password(user_domain_name='Default',
                            username='admin',
                            password='openstack',
                            project_domain_name='Default',
                            project_name='admin',
                            auth_url='http://{}:5000/v3'.format(keystone_ip))
 
sess = session.Session(auth=auth)
barbican = client.Client(session=sess, endpoint='http://{}:9311'.format(barbican_ip))
secret = barbican.secrets.create(name='Self destruction sequence',
                                 payload='the magic words are squeamish ossifrage',
                                 payload_content_type='text/plain')
secret.store()
print(secret.secret_ref)
ref = secret.secret_ref.replace('localhost', barbican_ip)
retrieved_secret = barbican.secrets.get(secret.secret_ref)
print(retrieved_secret.payload)
