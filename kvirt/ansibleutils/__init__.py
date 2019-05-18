#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
interact with a local/remote libvirt daemon
"""

import os
import time
from kvirt.common import pprint
from yaml import dump


def play(k, name, playbook, variables=[], verbose=False, user=None, tunnel=False, tunnelhost=None, tunnelport=None,
         tunneluser=None, yamlinventory=False):
    """

    :param k:
    :param name:
    :param playbook:
    :param variables:
    :param verbose:
    :param tunnelhost:
    :param tunnelport:
    :param tunneluser:
    """
    counter = 0
    while counter != 80:
        ip = k.ip(name)
        if ip is None:
            time.sleep(5)
            pprint("Retrieving ip of %s..." % name)
            counter += 10
        else:
            break
    login = k._ssh_credentials(name)[0] if user is None else user
    if yamlinventory:
        info = {'ansible_user': login}
        inventoryfile = "/tmp/%s.inv.yaml" % name
        if '.' in ip:
            info['ansible_host'] = ip
        else:
            info['ansible_host'] = '127.0.0.1'
            info['ansible_port'] = ip
        inventory = {'ungrouped': {'hosts': {name: info}}}
    else:
        inventoryfile = "/tmp/%s.inv" % name
        if '.' in ip:
            inventory = "%s ansible_host=%s ansible_user=%s" % (name, ip, login)
        else:
            inventory = "%s ansible_host=127.0.0.1 ansible_user=%s ansible_port=%s" % (name, login, ip)
    ansiblecommand = "ansible-playbook"
    if verbose:
        ansiblecommand = "%s -vvv" % ansiblecommand
    if variables is not None:
        for variable in variables:
            if not isinstance(variable, dict) or len(list(variable)) != 1:
                continue
            else:
                key, value = list(variable)[0], variable[list(variable)[0]]
                if yamlinventory:
                    inventory['ungrouped']['hosts'][name][key] = value
                else:
                    inventory += " %s=%s" % (key, value)
    if tunnel and tunnelport and tunneluser:
        tunnelinfo = "-o ProxyCommand=\"ssh -p %s -W %%h:%%p %s@%s\"" % (tunnelport, tunneluser, tunnelhost)
        if yamlinventory:
            inventory['ungrouped']['hosts'][name]['ansible_ssh_common_args'] = tunnelinfo
        else:
            inventory += " ansible_ssh_common_args='%s'" % tunnelinfo
    with open(inventoryfile, 'w') as f:
        if yamlinventory:
            dump(inventory, f, default_flow_style=False)
        else:
            f.write("%s\n" % inventory)
    pprint("Ansible Command run:")
    pprint("%s -T 20 -i %s %s" % (ansiblecommand, inventoryfile, playbook))
    os.system("%s -T 20 -i %s %s" % (ansiblecommand, inventoryfile, playbook))


def vm_inventory(self, name, user=None, yamlinventory=False):
    """

    :param self:
    :param name:
    :return:
    """
    counter = 0
    while counter != 80:
        ip = self.ip(name)
        if ip is None:
            time.sleep(5)
            pprint("Retrieving ip of %s..." % name)
            counter += 10
        else:
            break
    login = self._ssh_credentials(name)[0] if user is None else user
    info = {'ansible_user': login} if yamlinventory else ''
    if ip is not None:
        if '.' in ip:
            if yamlinventory:
                info['ansible_host'] = ip
            else:
                info = "%s ansible_host=%s ansible_user=%s" % (name, ip, login)
        else:
            if yamlinventory:
                info['ansible_host'] = '127.0.0.1'
                info['ansible_port'] = ip
            else:
                info = "%s ansible_host=127.0.0.1 ansible_user=%s ansible_port=%s" % (name, login, ip)
        return info
    else:
        return None


def make_plan_inventory(k, plan, vms, groups={}, user=None, tunnel=False, tunnelhost=None, tunnelport=None,
                        tunneluser=None, yamlinventory=False):
    """

    :param k:
    :param plan:
    :param vms:
    :param groups:
    :param user:
    :param tunnel:
    :param tunnelhost:
    :param tunnelport:
    :param tunneluser:
    """
    inventory = {} if yamlinventory else ''
    inventoryfile = "/tmp/%s.inv.yaml" % plan if yamlinventory else "/tmp/%s.inv" % plan
    if groups:
        if yamlinventory:
            inventory[plan] = {'children': {}}
        else:
            inventory += "[%s:children]\n" % plan
        for group in groups:
            if yamlinventory:
                inventory[plan]['children'][group] = {}
            else:
                inventory += "%s\n" % group
        for group in groups:
            nodes = groups[group]
            if yamlinventory:
                inventory[plan]['children'][group]['hosts'] = {}
            else:
                inventory += "[%s]\n" % group
            for name in nodes:
                inv = vm_inventory(k, name, user=user, yamlinventory=yamlinventory)
                if inv is not None:
                    if yamlinventory:
                        inventory[plan]['children'][group]['hosts'][name] = inv
                    else:
                        inventory += "%s\n" % inv
    else:
        if yamlinventory:
            inventory[plan] = {'hosts': {}}
        else:
            inventory += "[%s]\n" % plan
        for name in vms:
            inv = vm_inventory(k, name, user=user, yamlinventory=yamlinventory)
            if inv is not None:
                if yamlinventory:
                    inventory[plan]['hosts'][name] = inv
                else:
                    inventory += "%s\n" % inv
    if tunnel:
        tunnelinfo = "-o ProxyCommand=\"ssh -p %s -W %%h:%%p %s@%s\"" % (tunnelport, tunneluser, tunnelhost)
        if yamlinventory:
            if groups:
                for group in groups:
                    inventory[plan]['children'][group]['vars'] = {'ansible_ssh_common_args': tunnelinfo}
            else:
                inventory[plan]['vars'] = {'ansible_ssh_common_args': tunnelinfo}
        else:
            inventory += "[%s:vars]\n" % plan
            inventory += "ansible_ssh_common_args='%s'" % tunnelinfo
    with open(inventoryfile, "w") as f:
        if yamlinventory:
            dump(inventory, f, default_flow_style=False)
        else:
            f.write("%s\n" % inventory)
