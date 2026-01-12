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
---

## 15. Требования к детальным ТЗ по разделам (подмодулям/компонентам)

> Текущее ТЗ описывает **общую концепцию** платформы.  
> Для каждого крупного раздела (COGS, Settlements, VAT, Trade Docs, Print Platform, FA/MNA/MSHP и т.д.) требуется отдельное **детальное ТЗ** по единому шаблону (чтобы ИИ мог генерировать код без дополнительных вопросов).

### 15.1 Единый формат детального ТЗ (шаблон USER → CHAT)

Для каждого раздела/подмодуля создаётся отдельный Markdown-файл, заполняется **только секция USER**, секции CHAT заполняет ИИ автоматически.

Шаблон детального ТЗ (использовать как основу файла):

```md
# Odoo Module Specification (USER → CHAT)

> ⚠️ **Инструкция**
> - Заполняйте **только секции USER**
> - Секции CHAT заполняются автоматически ChatGPT
> - Если поле непонятно — оставьте пустым

---

## 0) Общие правила
- Один файл = один модуль
- Пользовательские названия можно писать на любом языке
- Технические имена будут сгенерированы автоматически

---

# 1) MODULE

## 1.1 USER
| Поле | Значение |
|---|---|
| Пользовательское название модуля | |
| Короткое описание (1 строка) | |
| Полное описание (3–10 строк) | |
| Категория (Tools / Sales / HR / Other) | |
| Используемые подсистемы (человечески) | |
| Нужны меню? (да/нет) | да |
| Нужны права доступа? (да/нет) | да |
| Демо-данные? (да/нет) | нет |

## 1.2 CHAT
```yaml
module:
  technical_name:
  version:
  depends:
  manifest:
```

---

# 2) MODELS

## 2.1 USER
| Пользовательское название модели | Назначение | Chatter (да/нет) | Archive (да/нет) | Название записи |
|---|---|---|---|---|
| | | нет | да | |

## 2.2 CHAT
```yaml
models: []
```

---

# 3) FIELDS

## 3.1 USER
> Для каждой модели — отдельная таблица

### Модель: ______________________

| Пользовательское имя поля | Тип поля | Обязательно | Уникально | Подсказка | Значение по умолчанию | Связь / варианты |
|---|---|---|---|---|---|---|
| | Char | да | нет | | | |

**Типы полей:**
Char, Text, Html, Integer, Float, Monetary, Boolean,
Date, Datetime, Selection,
Many2one, One2many, Many2many,
Binary, Image, Json

## 3.2 CHAT
```yaml
fields: []
```

---

# 4) UI (Меню и экраны)

## 4.1 USER
| Параметр | Значение |
|---|---|
| Название главного меню | |
| Иконка меню (если знаете) | |
| Какие модели в меню | |
| Экраны (tree/form/search/kanban) | tree, form |
| Нужны отчёты (pivot/graph)? | нет |

## 4.2 CHAT
```yaml
ui: {}
```

---

# 5) SECURITY

## 5.1 USER
| Роль | Описание | Доступ |
|---|---|---|
| Пользователь | | read/write |
| Менеджер | | full |

## 5.2 CHAT
```yaml
security: {}
```

---

# 6) LOGIC / BUTTONS

## 6.1 USER
| Модель | Описание логики |
|---|---|
| | |

## 6.2 CHAT
```yaml
logic: {}
```

---

# 7) DEMO DATA (опционально)

## 7.1 USER
| Модель | Примеры записей |
|---|---|
| | |

## 7.2 CHAT
```yaml
demo: []
```

---

## ✅ Результат
После заполнения этого файла ChatGPT сможет:
- сгенерировать полноценный модуль Odoo
- создать модели, поля, security
- создать tree/form/search views
- добавить stubs методов
- подготовить модуль к установке без доп. вопросов
```

### 15.2 Обязательные дополнения к шаблону для нашей платформы

К каждому детальному ТЗ (кроме заполненного шаблона выше) **обязательно** добавлять в конце файла следующие разделы:

1. **INTEGRATION (Platform Contracts)**
   - Какие модели/сервисы платформы используются (EntryBuilder, PostingEngine, OSVService, ReglamentEngine, PrintService).
   - Какие *provider*-ы регистрируются (COGSProvider / SettlementsProvider / VATProvider / DepreciationProvider / ClosingProvider).
   - Какие `dimension.type` и схемы субконто требуются/расширяются.

2. **LEDGER IMPACT (Проводки)**
   - Список типовых проводок, которые создаёт раздел (счета Дт/Кт, какие dimension_set на каждой стороне).
   - Что является **факт-проводками** (origin=document), что **регламентными** (origin=reglament).

3. **REGLEMENT (Draft / Period / Cron)**
   - Поведение расчёта при проведении документа (draft).
   - Поведение пересчёта за период (wizard).
   - Поведение nightly cron (период по умолчанию, стратегия scope, логирование).

4. **DRILLDOWN & EXPLAINABILITY**
   - Что пользователь видит в drilldown (entries → document_ref).
   - Какие allocation/распределения сохраняются для объяснения результата (FIFO allocations, оплатные allocations, VAT allocations).

5. **PRINT FORMS (если применимо)**
   - Какие XLSX-шаблоны нужны.
   - Список именованных областей и табличных блоков.

### 15.3 Правила качества для детальных ТЗ (обязательные)

- Детальное ТЗ должно быть **однозначным**: без “возможно/примерно”, только фиксированные требования.
- Любое влияние на бухгалтерию описывается как **ledger-эффект** (проводки + аналитика).
- Любая аналитика описывается как **dimension_set** по схеме счета.
- Любая регламентная логика обязана быть идемпотентной (повторный запуск даёт тот же результат) и помечать результаты `regl_run_id`.
- Для каждого раздела обязателен набор минимальных тест-кейсов (3–10 сценариев) и критерии приёмки.

### 15.4 Нейминг детальных ТЗ файлов (рекомендовано)

```text
spec/
  00_platform_core.md
  01_osv_engine.md
  02_posting_engine.md
  03_trade_docs.md
  04_cogs_provider.md
  05_settlements_provider.md
  06_vat_provider.md
  07_print_platform.md
  08_fa.md
  09_mna.md
  10_mshp.md
  11_month_closing.md
```

