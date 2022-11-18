import json

import pynetbox
from flask import Flask, request
from loguru import logger

import settings
from zabbix import ZabbixNBN

app = Flask(__name__)


@app.route("/webhook/", methods=['POST'])
def webhook():

    """{"event": "updated",
    "timestamp": "2022-08-06 16:48:22.083260+00:00",
    "model": "device",
    "username": "vlad",
    "request_id": "8da55b33-236a-48ab-a4eb-f73d8493e2d8",
    "data": {"id": 1, "url": "/api/dcim/devices/1/", "display": "m9-r0", "name": "m9-r0", "device_type": {"id": 1, "url": "/api/dcim/device-types/1/", "display": "MX960", "manufacturer": {"id": 1, "url": "/api/dcim/manufacturers/1/", "display": "Juniper", "name": "Juniper", "slug": "juniper"}, "model": "MX960", "slug": "mx960"}, "device_role": {"id": 1, "url": "/api/dcim/device-roles/1/", "display": "Router", "name": "Router", "slug": "router"}, "tenant": null, "platform": null, "serial": "", "asset_tag": null, "site": {"id": 1, "url": "/api/dcim/sites/1/", "display": "Home", "name": "Home", "slug": "home"}, "location": null, "rack": null, "position": null, "face": null, "parent_device": null, "status": {"value": "active", "label": "Active"}, "airflow": {"value": "front-to-rear", "label": "Front to rear"}, "primary_ip": null, "primary_ip4": null, "primary_ip6": null, "cluster": null, "virtual_chassis": null, "vc_position": null, "vc_priority": null, "comments": "", "local_context_data": null, "tags": [], "custom_fields": {}, "created": "2022-08-06T16:42:58.691288Z", "last_updated": "2022-08-06T16:48:22.055581Z"}, "snapshots": {"prechange": {"created": "2022-08-06T16:42:58.691Z", "last_updated": "2022-08-06T16:47:33.673Z", "local_context_data": null, "device_type": 1, "
    """

    netbox_alert = json.loads(request.data)

    if not netbox_alert['model'] == 'device':
        return ''

    alert_type = netbox_alert['event']
    device_id = netbox_alert['data']['id']
    # device_ip = netbox_alert['data']['primary_ip4']
    # device_cf = netbox_alert['data']['custom_fields']['monitoring_class']
    # device_status = netbox_alert['data']['status']['value']

    if alert_type == 'update':
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

        nb_host = nb.dcim.devices.get(device_id)

        nb_host_ip = nb_host.primary_ip4.address.split('/')[0]
        nb_host_cf = nb_host.custom_fields.get('monitoring_class')

        group_ids = settings.CF_MAP[nb_host_cf]['groups']
        template_ids = settings.CF_MAP[nb_host_cf]['templates']

        zhost = z.get_host_by_name(nb_host.name) or z.get_hosts_by_ip(nb_host_ip)

        if zhost:
            z.update_host(zhost, template_ids, group_ids, nb_host.name, nb_host.status)
        else:
            z.create_host(nb_host.name, nb_host_ip, group_ids, template_ids)

    return ''


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=9000, debug=True)
