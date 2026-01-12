# Техническое задание
## Профессиональная бухгалтерская платформа для Odoo 18 Community
### Архитектура «Платформа + прикладные модули» (аналог 1С)

---

## 0. Общие принципы
1. Разрабатывается **платформа бухгалтерского учёта**, а не отдельный модуль.
2. Архитектура разделена на:
   - платформенный модуль (ядро),
   - прикладные модули (торговля, услуги, ОС, МНА, МШП, НДС и т.д.).
3. Учёт строится **исключительно на проводках (ledger)**.
4. Документы фиксируют факт, расчёты выполняются регламентно.
5. Себестоимость, взаиморасчёты и НДС — **пересчитываемые регламентные операции**.
6. Поддержка:
   - двойной записи,
   - N аналитик (субконто),
   - FIFO / средняя,
   - линейных уравнений для балансировки.
7. ОСВ — ledger-отчёт, не pivot.
8. QWeb не используется для печатных форм.

---

## 1. Модульная архитектура

### 1.1 Базовый платформенный модуль
**ukr_account_platform**

Содержит:
- план счетов (абстрактный),
- типы аналитик (dimension),
- схемы субконто,
- dimension_set,
- проводки (ledger),
- движки: Posting, OSV, Reglament,
- API для прикладных модулей,
- ОСВ с drilldown.

Не содержит отраслевых документов.

---

### 1.2 Прикладные модули
- ukr_account_trade — товары, ПТУ, РТУ, возвраты, COGS
- ukr_account_services — услуги
- ukr_account_settlements — взаиморасчёты 36/63
- ukr_account_vat — НДС UA
- ukr_account_fa — основные средства
- ukr_account_mna — МНА
- ukr_account_mshp — МШП
- ukr_account_ua_coa — план счетов UA и типовые схемы

---

## 2. Платформенное ядро данных

### 2.1 План счетов
ukr.account:
- code, name, parent_id
- account_type
- company_id
- active

### 2.2 Типы аналитик
ukr.dimension.type:
- code
- name
- target_model
- company_id
- active

### 2.3 Схемы субконто
ukr.account.schema / ukr.account.schema.line:
- account_id
- side (debit/credit/both)
- dimension_type_id
- required
- sequence

### 2.4 Dimension Set
ukr.dimension.set:
- company_id
- schema_id
- key_text
- key_hash
- display_name

ukr.dimension.set.line:
- dimension_type_id
- res_model
- res_id
- sequence

### 2.5 Проводки
ukr.entry:
- date
- company_id
- state
- amount
- debit_account_id
- credit_account_id
- debit_dimension_set_id
- credit_dimension_set_id
- document_ref
- origin
- regl_kind
- regl_run_id

---

## 3. Платформенные движки

### 3.1 Posting Engine
Единый механизм проведения документов с валидацией схем субконто.

### 3.2 EntryBuilder
API для создания проводок:
- add()
- set_debit_dims()
- set_credit_dims()
- set_document_ref()
- commit()

### 3.3 OSV Engine
Считает:
- сальдо на начало,
- обороты,
- сальдо на конец.

Ключ строки ОСВ: (account_id, dimension_set_id).

### 3.4 Drilldown
Из ОСВ → проводки → документ.

---

## 4. Регламентный движок

### 4.1 Модель запуска
ukr.regl.run:
- run_type
- company_id
- period
- state
- triggered_by
- log

### 4.2 Единый API
ReglamentEngine.run(run_type, company, period, mode, options)

---

## 5. Себестоимость (COGS)

- FIFO / средняя — основной алгоритм движения.
- Линейные уравнения — балансировка.
- Партия обязательна в ПТУ, необязательна в РТУ.
- FIFO подбирает партии автоматически.

Режимы:
- draft — локально при проведении,
- period — визард за период,
- cron — автоматический пересчёт.

---

## 6. Взаиморасчёты 36/63
- Основаны на системе линейных уравнений.
- FIFO используется только как приоритет.
- Режимы: draft / period / cron.

---

## 7. НДС
- Первое/второе событие,
- корректировки,
- распределение по периодам,
- отдельный VATProvider.

---

## 8. Документы торговли
- ПТУ
- РТУ
- Возврат поставщику
- Возврат покупателя
- Платёжные документы

---

## 9. Перемещение
- По умолчанию используется stock Odoo.
- Бух-перемещение 281→281 — опциональный модуль.

---

## 10. Печатные формы

### 10.1 Отдельный модуль
ukr_print_platform

### 10.2 Макеты
- XLSX / ODS
- Excel-подобная верстка
- именованные области

### 10.3 API
PrintService.render(template_code, record, output)

PDF формируется через LibreOffice headless.

---

## 11. Производительность
Индексы:
- ukr.entry(date, company_id)
- debit_account_id + debit_dimension_set_id + date
- credit_account_id + credit_dimension_set_id + date
- dimension_set.key_hash UNIQUE

---

## 12. Этапы разработки
1. Каркас платформы
2. Аналитика и dimension_set
3. Ledger и EntryBuilder
4. OSV Engine
5. Drilldown
6. Reglament Engine
7. COGS Provider
8. Settlements Provider
9. Документы торговли
10. Печатные формы
11. Тесты и аудит

---

## 13. Философия
Документ — факт.  
Проводка — истина.  
Регламент — пересчитываемый.  
ОСВ — состояние системы.  
Платформа — основа, модули — расширения.
