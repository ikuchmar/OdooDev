===
## show-database-size
---
categories: DB - PostgreSQL - Admin
aliases: db size, pg size
Размер базы: `SELECT pg_size_pretty(pg_database_size('dbname'));`
```sql
SELECT pg_size_pretty(pg_database_size('postgres'));
```

---

## biggest-tables
categories: DB - PostgreSQL - Admin
aliases: table size
Таблицы, занимающие больше места: пример запроса.
```sql
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 10;
```
