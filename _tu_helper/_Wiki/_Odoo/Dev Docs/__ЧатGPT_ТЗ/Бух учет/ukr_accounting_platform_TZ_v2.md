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
---

## 14. Требования к генерации кода, моделей и структуры модуля (стиль `smk_constructor`)

> Этот раздел обязателен для ИИ‑генерации кода и должен соблюдаться во всех модулях платформы и прикладных аддонах.

### 14.1 Компонентная структура модуля (обязательная)

Вместо плоских папок `models/`, `views/`, `security/` в корне используется **компонентная структура**:

```text
<target_module>/
  __init__.py
  __manifest__.py
  components/
  wizards/
  menus/
  static/
  hooks.py              # если есть hooks
```

Компоненты (domain components):

```text
components/
  __init__.py
  tools/                # только утилиты, НЕ модели
    __init__.py
    *.py
  <component_key>/
    __init__.py
    models/
      __init__.py
      <component_key>_model.py
      <component_key>_methods.py
    views/
      *.xml
    actions/
      *.xml
    menus/
      *.xml
    security/
      security.xml
      ir.model.access.csv
    data/
      *.xml
```

Визарды живут в отдельной ветке и имеют такую же мини‑структуру:

```text
wizards/
  __init__.py
  <wizard_key>/
    __init__.py
    models/
      __init__.py
      *.py
    views/
      *.xml
    actions/
      *.xml
    menus/
      *.xml
    security/
      security.xml
      ir.model.access.csv
```

**Важно:** `components/tools/` — только утилиты (model‑agnostic). Они **не импортируются автоматически** через `components/__init__.py`.

### 14.2 Правила импортов (`__init__.py`) — без циклов

- `<target_module>/__init__.py` импортирует только `components` (и при необходимости `wizards`, `hooks`)
- `components/__init__.py` импортирует только компоненты с моделями и **не импортирует** `tools/`
- `components/<component>/models/__init__.py` импортирует сначала файл с полями (`*_model.py`), потом методы (`*_methods.py`) через `_inherit`

### 14.3 Security — внутри компонента/визарда

- У каждого компонента свой `components/<component>/security/`
- У каждого визарда свой `wizards/<wizard>/security/`
- Запрещено централизовать security в одном месте, чтобы “не терялись” ACL/группы

### 14.4 Порядок подключения XML/CSV в `__manifest__.py` (строго)

Рекомендуемый порядок:

1. `menus/constructor_root_menu.xml` (root‑меню)
2. `components/**/security/ir.model.access.csv`
3. `wizards/**/security/ir.model.access.csv`
4. `components/**/security/security.xml`
5. `wizards/**/security/security.xml`
6. `components/**/views/*.xml`
7. `wizards/**/views/*.xml`
8. `components/**/actions/*.xml`
9. `wizards/**/actions/*.xml`
10. `components/**/menus/*.xml`
11. `wizards/**/menus/*.xml`
12. `components/**/data/*.xml` (и прочие data)

Все файлы перечислять **явно**, без автопоиска.

### 14.5 Стиль объявлений полей (ВАЖНО, строго)

**Единственно допустимый формат** (перенос строки между `fields.Xxx` и первым аргументом запрещён):

```python
import_state = fields.Selection(selection=[("not_imported", "Not Imported"),
                                           ("partial", "Partial"),
                                           ("imported", "Imported"),
                                           ("outdated", "Outdated"),
                                           ("error", "Error")],
                                string="Import State",
                                default="not_imported",
                                readonly=True,
                                copy=False,
                                index=True,
                                )
```

Правила:
- `fields.Xxx(` всегда в той же строке, что и первый аргумент.
- Каждый параметр на отдельной строке с одинаковым отступом и запятой.
- Закрывающая `)` и запятая — на отдельной строке.

### 14.6 Комментарии и группировка полей

- Над каждым полем — RU‑комментарий “что это и зачем”.
- Поля группируются логическими секциями (Technical/State, Relations, Computed, UI helpers и т.д.).

### 14.7 Стиль методов

Большие смысловые блоки разделяются комментарием‑разделителем:

```python
# ================================
# Compute
# ================================
```

Код должен быть читаемым “средним программистом”, без усложнений ради красоты. Сложное выносить в `components/tools/` или helper‑методы.

### 14.8 Мини‑чеклист генерации

- компонентная структура соблюдена (нет плоских папок в корне)
- `tools/` не импортируется в `components/__init__.py`
- у каждого компонента и визарда свой `security/`
- в `__manifest__.py` порядок файлов соответствует 14.4
- поля оформлены строго по 14.5 + RU‑комментарии + группировка
- методы разделены `===============`

