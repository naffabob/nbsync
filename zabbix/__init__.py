import typing

from loguru import logger
from pyzabbix.api import ZabbixAPI, ZabbixAPIException

import settings


class ZabbixNBN:

    def __init__(self):
        self.zapi = ZabbixAPI(settings.ZABBIX_URL, user=settings.ZABBIX_USER, password=settings.ZABBIX_PASS)

        self.HOST_STATUS_ENABLE = '0'
        self.HOST_STATUS_DISABLE = '1'

    def get_hosts(self) -> typing.List[dict]:
        hosts = self.zapi.host.get(
            groupids=[settings.GROUP_NBSYNC_ID],
            output=['host', 'status', 'name'],
            selectGroups="groupid",
            selectParentTemplates='templateid',
            selectInterfaces='extend'
        )
        return hosts

    def get_hosts_by_ip(self, ip: str) -> typing.List[dict]:
        hostids = {
            host['hostid'] for host
            in self.zapi.hostinterface.get(filter={'ip': ip}, output=['hostid'])
        }
        hosts = self.zapi.host.get(
            hostids=list(hostids),
            output=['host', 'status'],
            selectGroups="groupid",
            selectParentTemplates='templateid',
            selectInterfaces='extend',
        )
        return hosts

    def create_host(self, hostname: str, ip: str, groupids: typing.List[int], templateids: typing.List[int]):
        target_groups = set(groupids)
        target_groups.add(settings.GROUP_NBSYNC_ID)

        groups = [{'groupid': x} for x in target_groups]
        interfaces = [
            {
                'ip': ip,
                'main': 1,
                'type': 2,  # SNMP type interfaces
                'useip': 1,
                'dns': '',
                'port': '161',
                'details': {
                    'version': '2',  # SNMP version
                    'bulk': '1',
                    'community': settings.COMMUNITY
                }
            }
        ]
        if settings.DONT_ASK or input(f"Create host {hostname}. Confirm? y/n: ") == 'y':
            try:
                self.zapi.host.create(
                    host=hostname,
                    name=hostname,
                    groups=groups,
                    templates=templateids,
                    interfaces=interfaces,
                )

            except ZabbixAPIException as e:
                data = e.args[0]
                logger.error(f"Zabbix error while creating host {hostname}: {data['message']} {data['data']}")
                raise

            else:
                logger.info(f'Created host {hostname}')

    def close(self):
        self.zapi.user.logout()

    def diff(self, old: dict, new: dict) -> str:
        result = []
        for k, v in old.items():
            if v != new[k]:
                result.append(f'{k}: {v}->{new[k]}')
        return ', '.join(result)

    def update_host_interface(self, host_iface: dict, ip: str):
        target_iface = {
            'interfaceid': host_iface['interfaceid'],
            'type': '2',
            'useip': '1',
            'main': '1',
            'hostid': host_iface['hostid'],
            'ip': ip,
            'dns': '',
            'port': '161',
            'details': {'version': '2', 'bulk': '1', 'community': settings.COMMUNITY}
        }
        if host_iface == target_iface:
            return
        changes = self.diff(host_iface, target_iface)
        if settings.DONT_ASK or input(f"Hostid {host_iface['hostid']}: {changes} Confirm? y/n: ") == 'y':
            self.zapi.hostinterface.update(target_iface)
            logger.info(f"Hostid {host_iface['hostid']} interface updated: {changes}")

    def delete_host_interface(self, host_iface):
        host_iface_id = host_iface['interfaceid']
        if settings.DONT_ASK or input(f"{host_iface['hostid']} delete_host_interface. Confirm? y/n: ") == 'y':
            self.zapi.hostinterface.delete(host_iface_id)
            logger.info(f"Hostid {host_iface['hostid']} interface deleted")

    def replace_host_template(self, host: dict, host_template_ids: typing.List[int]):
        target_templates = {str(x) for x in host_template_ids}
        host_templates = {x['templateid'] for x in host['parentTemplates']}
        if host_templates == target_templates:
            return

        name = host['host']
        if (
                settings.DONT_ASK or
                input(f"{name} {host_templates} > {target_templates}. Confirm? y/n: ") == 'y'
        ):
            self.zapi.host.update(hostid=host['hostid'], templates=host_template_ids)
            logger.info(f"{name} templates replaced {host_templates} > {target_templates}")

    def replace_host_group(self, host: dict, group_ids: typing.List[int]):
        target_groups = set(group_ids)
        target_groups.add(settings.GROUP_NBSYNC_ID)

        host_groups = {int(x['groupid']) for x in host['groups']}
        if host_groups == target_groups:
            return

        name = host['host']
        if (
                settings.DONT_ASK or
                input(f"{name} replace group {host_groups} > {target_groups}. Confirm? y/n: ") == 'y'
        ):
            self.zapi.host.update(hostid=host['hostid'], groups=[{'groupid': x} for x in target_groups])
            logger.info(f"{name} groups replaced {host_groups} > {target_groups}")

    def update_hostname(self, host: dict, hostname: str):
        old_name = host['host']
        if hostname == old_name:
            return

        if settings.DONT_ASK or input(f"{old_name} update hostname. Confirm? y/n: ") == 'y':
            self.zapi.host.update(hostid=host['hostid'], host=hostname)
            logger.info(f"{old_name} hostname updated {old_name} > {hostname}")

    def update_host_status(self, host: dict, status: str):
        if status == host['status']:
            return

        name = host['host']
        if settings.DONT_ASK or input(f"{name} status update {host['status']} > {status}. Confirm? y/n: ") == 'y':
            self.zapi.host.update(hostid=host['hostid'], status=status)
            logger.info(f"{name} status updated {host['status']} > {status}")
