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
            output=['host', 'status'],
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

    def create_host(self, hostname: str, ip: str, groupid: int, templateids: list):
        groups = [{'groupid': groupid}, {'groupid': settings.GROUP_NBSYNC_ID}]
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

    def close(self):
        self.zapi.user.logout()

    def update_host_interface(self, host_iface: dict, ip: str):
        self.zapi.hostinterface.update(
            interfaceid=host_iface['interfaceid'],
            type=2,
            ip=ip,
            dns='',
            port='161',
            details={'version': '2', 'bulk': '1', 'community': settings.COMMUNITY},
        )

    def delete_host_interface(self, host_iface):
        host_iface_id = host_iface['interfaceid']
        self.zapi.hostinterface.delete(host_iface_id)

    def replace_host_template(self, host: dict, host_template_ids: list):
        self.zapi.host.update(hostid=host['hostid'], templates=host_template_ids)

    def replace_host_group(self, host: dict, host_group_id: str):
        self.zapi.host.update(
            hostid=host['hostid'],
            groups=[{'groupid': host_group_id}, {'groupid': settings.GROUP_NBSYNC_ID}]
        )

    def update_host_name(self, host: dict, hostname: str):
        self.zapi.host.update(hostid=host['hostid'], host=hostname, name=hostname)

    def update_host_status(self, host: dict, status: str):
        ex_status = host['status']
        if ex_status == status:
            return
        self.zapi.host.update(hostid=host['hostid'], status=status)
