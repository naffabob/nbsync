import typing

import pynetbox
from loguru import logger
from pynetbox.models.dcim import Devices

import settings
from zabbix import ZabbixNBN

logger.add(
    settings.LOG_FILE,
    level=settings.LOG_LEVEL,
    format="{time} {level} {message}",
    rotation="10 KB",
    compression="zip",
)


def get_nb_hosts() -> typing.List:
    # Get active hosts with monitoring class field
    all_devices = []
    for c in settings.NB_MONITORING_CFS:
        devs = nb.dcim.devices.filter(status='active', cf_monitoring_class=c)
        all_devices.extend(devs)
    return all_devices


def update_host(host: Devices):
    cf = host.custom_fields.get('monitoring_class')

    if cf not in settings.NB_MONITORING_CFS:
        logger.error(f'{host.name} has no correct Custom field')
        return

    if cf not in settings.CF_TO_GROUP:
        logger.error(f'No Zabbix Group for Custom field {cf}')
        return

    if cf not in settings.CF_TO_TEMPLATES:
        logger.error(f'No Zabbix Template for Custom field {cf}')
        return

    if host.primary_ip4 is None:
        logger.error(f'{host.name} has no Management primary IPv4')
        return

    ip = host.primary_ip4.address.split('/')[0]
    group_id = settings.CF_TO_GROUP[cf]
    template_ids = settings.CF_TO_TEMPLATES[cf]
    z_host_id = z.get_host_id_by_hostname(host.name)

    # If hostname exist
    if z_host_id:
        z_host_iface_ids = z.get_iface_ids_by_host_id(z_host_id)
        # Can be more than one interface. If so: first be modified, other deleted.

        z.update_host_interface(z_host_iface_ids[0], ip)

        for iface_id in z_host_iface_ids[1:]:
            z.delete_host_interface(iface_id)
            logger.info(f'Deleted interface on {host.name}')

        z.update_host_status(z_host_id, z.HOST_STATUS_ENABLE)
        z.replace_host_template(z_host_id, template_ids)
        z.replace_host_group(z_host_id, group_id)

    else:
        z_host_ifaces_with_ip = z.get_host_ifaces_by_ip(ip)

        if len(z_host_ifaces_with_ip) == 0:
            z.create_host(host.name, ip, group_id, template_ids)
            logger.info(f'Created host {host.name}')
            return

        elif len(z_host_ifaces_with_ip) == 1:
            z_host_id = z.get_host_id_from_host_ifaces(z_host_ifaces_with_ip)
            z_host_iface_id = z_host_ifaces_with_ip[0]['interfaceid']
            z.update_host_name(z_host_id, host.name)
            z.update_host_interface(z_host_iface_id, ip)
            z.update_host_status(z_host_id, z.HOST_STATUS_ENABLE)
            z.replace_host_template(z_host_id, template_ids)
            z.replace_host_group(z_host_id, group_id)

        elif len(z_host_ifaces_with_ip) > 1:
            logger.warning(f'> 2 hosts in zabbix with the same IP. {z_host_ifaces_with_ip}')
            return


if __name__ == '__main__':
    nb = pynetbox.api(settings.NB_URL, settings.NB_API_TOKEN)
    z = ZabbixNBN()

    # For real life code
    nb_hosts = get_nb_hosts()

    for nb_host in nb_hosts:
        update_host(nb_host)

    z.close()
