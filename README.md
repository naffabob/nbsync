# nbsync

## Что это
nbsync (netbox synchronizer) — автоматическое добавление девайсов из Netbox в Zabbix.

С помощью использования CustomFields в [Netbox](https://github.com/netbox-community/netbox), задаются параметры:
группы и шаблоны мониторинга в Zabbix.

## Настйроки
settings.py: Сопоставление мониторинг-классов с группами и шаблонами заббикса
(пример можно посмотреть в [settings_example.py](settings_example.py))

Опции файла настроек settings.py:
DONT_ASK
- True: Скрипт будет отрабатывать без запроса подтверждения вносимых изменений.
- False: Полезно при отладке. Скрипт будет запрашивать подтверждения вносимых изменений.

## Установка
Скачайте проект с bitbucket.org
```commandline
git clone https://naffabob@bitbucket.org/naffabob/nbsync.git
```
Создайте виртуальное окружение и установите зависимости для подходящей версии python
```commandline
pip install -r requirements_py36.txt
pip install -r requirements_py39.txt
```

## Запуск
Исполняемый файл [netbox_to_zabbix.py](netbox_to_zabbix.py)
Запустите его для разового добавления девайсов.

Либо добавьте в crontab автоматический запуск, например каждые 5 минут
```commandline
*/5 * * * * python netbox_to_zabbix.py 2>/dev/null
```
## Особенности
- Синхронизированные узлы будут иметь группу "NB Sync" в Zabbix.
- Удаление или выключение узла в Netbox'е сделает этот узел неактивным в Zabbix, чтобы не потерять данные мониторинга. 
Удаление неактивных узлов из заббикса предлагается выполнять вручную по мере накопления таких узлов.

## Дополнительная документация
[netbox](https://github.com/netbox-community/netbox)

[pynetbox](https://github.com/netbox-community/pynetbox)

[py-zabbix](https://github.com/adubkov/py-zabbix)