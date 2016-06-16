#!/usr/bin/python

from keystoneclient.v3 import (
    client,
    domains,
    projects,
    roles,
    users,
)
import os

class BarbicanDomain():
    def __init__(self, manager, reset=False):
        self.manager = manager
        self.domain = None
        self.update_domain()
        if reset:
            self.delete_domain()
        if not self.domain:
            self.create_domain()
        self.update_domain()

    def update_domain(self):
        for dom in self.manager.list():
            if dom.name == "barbican-domain":
                self.domain = dom

    def create_domain(self):
        if not self.domain:
            self.manager.create("barbican-domain", description="domain for Barbican test", enabled=True)

    def delete_domain(self):
        if self.domain:
            print "Deleting testdomain"
            self.manager.update(self.domain, enabled=False)
            self.manager.delete(self.domain)
        self.domain = None 

class BarbicanProject():
    def __init__(self, manager, domain_id, reset=False):
        self.manager = manager
        self.domain_id = domain_id
        self.project = None
        self.update_project()
        if reset:
            self.delete_project()
        if not self.project:
            self.create_project()
        self.update_project()

    def update_project(self):
        for proj in self.manager.list():
            if proj.name == "barbican-project":
                self.project = proj

    def create_project(self):
        if not self.project:
            self.manager.create("barbican-project", domain=self.domain_id, description="Barbican Project", enabled=True)

    def delete_project(self):
        if self.project:
            print "Deleting testproject"
            self.manager.delete(self.project)
        self.project = None 


class BarbicanUser():
    def __init__(self, manager, domain_id, reset=False):
        self.manager = manager
        self.domain_id = domain_id
        self.user = None
        self.update_user()
        if reset:
            self.delete_user()
        if not self.user:
            self.create_user()
        self.update_user()

    def update_user(self):
        for user in self.manager.list():
            if user.name == "barbican-user":
                self.user = user

    def create_user(self):
        if not self.user:
            self.manager.create("barbican-user", domain=self.domain_id, description="Barbican Project", enabled=True, email="test-user@testcorp.com", password="changeit")

    def delete_user(self):
        if self.user:
            print "Deleting testuser"
            self.manager.delete(self.user)
        self.user = None 


def get_admin_role(manager):
    for role in manager.list():
        if role.name == "Admin":
            return role


if __name__ == '__main__':
    reset=False
    keystone = client.Client(user_domain_name='Default',
                             username=os.environ['OS_USERNAME'],
                             password=os.environ['OS_PASSWORD'],
                             project_domain_name='Default',
                             project_name='admin',
                             auth_url=os.environ['OS_AUTH_URL'])
    domain_manager = domains.DomainManager(keystone)
    project_manager = projects.ProjectManager(keystone)
    user_manager = users.UserManager(keystone)
    role_manager = roles.RoleManager(keystone)
    barbican_domain=BarbicanDomain(domain_manager, reset=reset)
    barbican_project=BarbicanProject(project_manager, barbican_domain.domain.id, reset=reset)
    barbican_user=BarbicanUser(user_manager, barbican_domain.domain.id, reset=reset)
    admin_role=get_admin_role(role_manager)
    role_manager.grant(admin_role.id,
		       user=barbican_user.user.id,
		       project=barbican_project.project.id)
    print "Domain ID: " + barbican_domain.domain.id
    print "Project ID: " + barbican_project.project.id
