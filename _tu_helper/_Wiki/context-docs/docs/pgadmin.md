==========================
## connect
==========================
pgAdmin - Подключение - Сервер
--------------------------------------------
Создание подключения к серверу PostgreSQL.

```text
Servers → Create → Server...
Name: Local PG
Connection → Host: localhost
Port: 5432
Maintenance DB: postgres
Username: postgres
Password: ****
```
## backup
pgAdmin - Операции - Бэкап
Создание резервной копии базы.

```text
Right click on DB → Backup...
Format: Custom
Filename: /backups/db_$(date +%F).backup
Role name: postgres
```
