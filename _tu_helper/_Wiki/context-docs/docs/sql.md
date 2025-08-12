==========================
## create-table
==========================
SQL - DDL - Создание таблиц
--------------------------------------------
Пример создания таблицы.

```sql
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT now()
);
```
## select-join
SQL - DQL - Запросы
Соединение таблиц.

```sql
SELECT u.name, o.total
FROM users u
JOIN orders o ON o.user_id = u.id
WHERE o.total > 100;
```
