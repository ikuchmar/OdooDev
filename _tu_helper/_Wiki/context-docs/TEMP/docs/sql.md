===
## join-types
---
categories: DB - SQL - JOIN
aliases: inner left right
Типы соединений: INNER, LEFT, RIGHT, FULL.
```sql
SELECT * FROM a INNER JOIN b ON a.id=b.a_id
```

---

## window-functions
categories: DB - SQL - Window
aliases: over, partition
Оконные функции позволяют вычислять агрегаты по окнам.
```sql
SELECT id, value, SUM(value) OVER (PARTITION BY grp ORDER BY id)
FROM t
```
