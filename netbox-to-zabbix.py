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


def get_nb_hosts() -> typing.List[Devices]:
    # Get active hosts with monitoring class field
    all_devices = []
    for c in settings.NB_MONITORING_CFS:
        devs = nb.dcim.devices.filter(status='active', cf_monitoring_class=c)
        all_devices.extend(devs)
    logger.debug(f'{len(all_devices)} hosts found in Netbox')
    return all_devices


def update_or_create_host(nbhost: Devices, zhost: typing.Optional[dict]):
    cf = nbhost.custom_fields.get('monitoring_class')

    if cf not in settings.NB_MONITORING_CFS:
        logger.error(f'{nbhost.name} has no correct Custom field')
        return

    if cf not in settings.CF_TO_GROUP:
        logger.error(f'No Zabbix Group for Custom field {cf}')
        return

    if cf not in settings.CF_TO_TEMPLATES:
        logger.error(f'No Zabbix Template for Custom field {cf}')
        return

    if nbhost.primary_ip4 is None:
        logger.error(f'{nbhost.name} has no Management primary IPv4')
        return

    logger.debug(f'Processing {nbhost.name}')
    ip = nbhost.primary_ip4.address.split('/')[0]
    group_id = settings.CF_TO_GROUP[cf]
    template_ids = settings.CF_TO_TEMPLATES[cf]

    if zhost:
        for iface in zhost['interfaces'][1:]:
            z.delete_host_interface(iface)

        z.update_host_interface(zhost['interfaces'][0], ip)

        z.update_host_status(zhost, z.HOST_STATUS_ENABLE)
        z.replace_host_template(zhost, template_ids)
        z.replace_host_group(zhost, group_id)

    else:
        zhosts = z.get_hosts_by_ip(ip)

        if len(zhosts) == 0:
            z.create_host(nbhost.name, ip, group_id, template_ids)
            logger.info(f'Created host {nbhost.name}')

        elif len(zhosts) == 1:
            zhost = zhosts[0]

            z.update_host_name(zhost, nbhost.name)

            for iface in zhost['interfaces'][1:]:
                z.delete_host_interface(iface)
            z.update_host_interface(zhost['interfaces'][0], ip)

            z.update_host_status(zhost, z.HOST_STATUS_ENABLE)
            z.replace_host_template(zhost, template_ids)
            z.replace_host_group(zhost, group_id)
            logger.debug(f"{zhost['host']} updated")

        elif len(zhosts) > 2:
            logger.warning(f"> 2 interfaces in zabbix with the same IP: {ip}")


if __name__ == '__main__':
    try:
        nb = pynetbox.api(settings.NB_URL, settings.NB_API_TOKEN)
    except Exception as e:
        logger.error(e)
        quit(1)

    try:
        z = ZabbixNBN()
    except Exception as e:
        logger.error(e)
        quit(1)

    zhosts_map = {zhost['host']: zhost for zhost in z.get_hosts()}

    nb_hosts = get_nb_hosts()

    for nb_host in nb_hosts:
        zhost = zhosts_map.get(nb_host.name)
        update_or_create_host(nb_host, zhost)

    # Disable not actual hosts in zabbix
    nb_hostnames = {dev.name for dev in nb_hosts}
    for zhost in z.get_hosts():
        hostname = zhost['host']
        if hostname not in nb_hostnames:
            z.update_host_status(zhost, z.HOST_STATUS_DISABLE)
            logger.info(f'{hostname} does not exists in Netbox. Was disabled in Zabbix.')
    z.close()
