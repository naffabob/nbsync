import typing

from pyzabbix.api import ZabbixAPI, ZabbixAPIException

import settings


class ZabbixNBN:
    HOST_STATUS_ENABLE = '0'
    HOST_STATUS_DISABLE = '1'

    zapi = ZabbixAPI(settings.ZABBIX_URL, user=settings.ZABBIX_USER, password=settings.ZABBIX_PASS)

    def create_host(self, hostname: str, ip: str, groupid: int, templateids: list):
        description = 'Generated automatically'
        groups = [{'groupid': groupid}]
        templates = templateids
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
                templates=templates,
                interfaces=interfaces,
                description=description,
            )
        except ZabbixAPIException as e:
            data = e.args[0]
            print(f"Zabbix error while creating host {hostname}: {data['message']} {data['data']}")

    def close(self):
        self.zapi.user.logout()

    def update_host_interface(self, host_iface_id: str, ip: str):
        self.zapi.hostinterface.update(
            interfaceid=host_iface_id,
            type=2,
            ip=ip,
            dns='',
            port='161',
            details={'version': '2', 'bulk': '1', 'community': settings.COMMUNITY},
        )

    def delete_host_interface(self, host_ifaces):
        host_iface_id = host_ifaces[0]['interfaceid']
        self.zapi.hostinterface.delete([host_iface_id])

    def replace_host_template(self, host_id: str, host_template_ids: list):
        self.zapi.host.update(hostid=host_id, templates=host_template_ids)

    def replace_host_group(self, host_id: str, host_group_id: str):
        self.zapi.host.update(hostid=host_id, groups=[{'groupid': host_group_id}])

    def update_host_name(self, host_id: str, hostname: str):
        self.zapi.host.update(hostid=host_id, host=hostname, name='')

    def update_host_status(self, host_id: str, status: str):
        self.zapi.host.update(hostid=host_id, status=status)

    def get_host_ifaces_by_ip(self, ip: str) -> list:
        return self.zapi.hostinterface.get(filter={'ip': ip})

    def get_iface_ids_by_host_id(self, host_id: str) -> list:
        ifaces_list = self.zapi.hostinterface.get(filter={'hostid': host_id})
        iface_ids_list = []
        for iface in ifaces_list:
            iface_ids_list.append(iface['interfaceid'])
        return iface_ids_list

    def get_host_id_by_hostname(self, hostname: str) -> typing.Optional[str]:
        host = self.zapi.host.get(filter={'host': hostname})
        if host:
            host_id = host[0]['hostid']
            return host_id
        return None

    def get_host_id_from_host_ifaces(self, zabbix_host_ifaces: list) -> str:
        return zabbix_host_ifaces[0]['hostid']

    def get_hostnames_by_group(self, groups: list) -> typing.List[str]:
        # Get active hosts from custom groups
        hosts = self.zapi.host.get(groupids=groups)
        hostnames = [host['host'] for host in hosts
                     if host['status'] == self.HOST_STATUS_ENABLE]
        return hostnames