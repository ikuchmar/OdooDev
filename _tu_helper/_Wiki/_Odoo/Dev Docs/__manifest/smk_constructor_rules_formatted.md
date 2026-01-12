# SMK / Odoo 18 — Правила структуры модуля (стиль `smk_constructor`)

Документ описывает **строгие правила** сборки нового Odoo 18 модуля в стиле `smk_constructor`, чтобы любой чат мог
**однозначно** понимать:

- какие папки/файлы создавать
- как их называть
- как подключать в `__manifest__.py`
- где хранить утилиты и как их использовать
- какие соглашения по Python‑коду и объявлениям полей соблюдать

---

## 0) Общая идея

Вместо плоской структуры:

- `models/`
- `views/`
- `security/`
- `data/`

используется **компонентная структура**:

- каждая доменная сущность — это **компонент**
- у компонента есть свои `models/`, `views/`, `actions/`, `menus/`, `security/`, `data/` (опционально)
- визарды (wizards) живут **в отдельной ветке** `wizards/` и **тоже имеют свою мини‑структуру** (как компоненты)
- общие утилиты лежат в `components/tools/` и **не импортируются автоматически**

---

## 1) Структура каталогов (обязательная)

### 1.1 Корень аддона

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

### 1.2 Компоненты (domain components)

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
      <component_key>_methods.py      # если нужны методы отдельно
    views/
      *.xml
    actions/
      *.xml
    menus/
      *.xml
    security/
      security.xml
      ir.model.access.csv
    data/                # опционально
      *.xml
```

### 1.3 Wizards (визарды)

```text
wizards/
  __init__.py
  common/               # опционально: общие визард‑утилиты/миксины
    __init__.py
    *.py
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

### 1.4 Menus (корневые меню)

```text
menus/
  constructor_root_menu.xml     # единый файл корневых меню (root/settings/sections)
```

### 1.5 Static

```text
static/
  description/
    icon.png
```

---

## 2) Правила импортов (`__init__.py`) — чтобы не было циклов

### 2.1 `<target_module>/__init__.py`

Импортирует **только** `components` (и при необходимости `wizards`, `hooks`):

```python
from . import components
from . import wizards
from . import hooks
```

### 2.2 `components/__init__.py`

Импортирует **только** компоненты с моделями.  
**НЕ** импортирует `tools/`.

```python
from . import constructor_type
from . import constructor_model
from . import constructor_field
```

### 2.3 `components/<component>/__init__.py`

```python
from . import models
```

### 2.4 `components/<component>/models/__init__.py`

Порядок важен:

1) сначала файл с полями (`*_model.py`)  
2) потом файл с методами (`*_methods.py`) через `_inherit`

```python
from . import constructor_field_model
from . import constructor_field_methods
```

---

## 3) Правила security (важное отличие)

### 3.1 Security хранится внутри компонента

НЕТ общей папки `components/security/`.

Для каждого компонента:

```text
components/<component>/security/
  security.xml
  ir.model.access.csv
```

### 3.2 Wizards тоже имеют свой `security/`

Иначе права “теряются”, если хранить их централизованно.

```text
wizards/<wizard>/security/
  security.xml
  ir.model.access.csv
```

---

## 4) `components/tools/` — правила общих утилит (как `autofill_magic.py`)

### 4.1 Назначение

`components/tools/` — общие функции, которые используются разными компонентами и визардами.

### 4.2 Ключевое правило

- утилиты должны быть **model‑agnostic**
- утилиты могут принимать `env` / `recordset` / словарь параметров
- утилиты **НЕ** должны импортировать модели конструктора, чтобы не создавать циклические импорты

**Нормально:**
- функции генерации строк манифеста (depends, data files)
- `slugify`, `humanize`, `suggest_*` имена
- сортировки/уникализация/парсеры

**Ненормально:**
- `from odoo.addons.<module>.components.<x>.models... import ...`

---

## 5) Нейминг моделей и классов (Python)

### 5.1 Модели (`_name`)

Префикс: `smk.constructor.<entity>` (или другой проектный префикс, но единообразно)

Примеры:
- `smk.constructor.type`
- `smk.constructor.model`
- `smk.constructor.field`

### 5.2 Классы

`SmkConstructor<Entity>` (CamelCase)

Пример:
- `SmkConstructorField`

### 5.3 Разделение файлов

**`<component>_model.py`:**
- `_name`, `_description`
- поля
- `_sql_constraints` (если есть)
- константы/списки (если надо)

**`<component>_methods.py`:**
- `_inherit = "..."` (расширение модели)
- compute / onchange / constraints / create/write/unlink / actions / helper‑логика

---

## 6) Нейминг XML‑файлов и XML ID

### 6.1 XML namespace

Всегда используем `module_name.<xml_id>` при ссылках:

- `ref="smk_constructor.some_id"`
- `action="smk_constructor.action_constructor_type"`

### 6.2 Views

Имена файлов — как в модуле:

- `..._form.xml`, `..._tree.xml`, `..._search.xml`
- иногда встречается `..._views.xml` или `..._views_form.xml` для специфических сущностей/наследований

Рекомендуемое правило:
- `<component>_form.xml`
- `<component>_tree.xml`
- `<component>_search.xml`

### 6.3 Actions

- `<component>_action.xml`

### 6.4 Menus

- `<component>_menu.xml`

### 6.5 XML ID (рекомендуемый паттерн)

- action: `action_<component>`
- menu: `menu_<component>`
- view: `<component>_view_form|tree|search`

---

## 7) Порядок подключения файлов в `__manifest__.py` (как в `smk_constructor`)

Факт по модулю: порядок допускает, что `menus/constructor_root_menu.xml` подключается первым.

Рекомендуемый стабильный порядок “как у нас принято”:

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

Главный принцип: в манифесте должны быть перечислены **все файлы явно**, без магии автопоиска.

---

## 8) Стиль объявления полей (ВАШИ предпочтения — обязательны)

### 8.1. Форматирование объявлений полей (fields.*)

Все поля моделей Odoo обязаны объявляться в строго фиксированном многострочном формате.

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




Обязательные правила

Открывающая скобка ( всегда остаётся в той же строке, что и fields.Xxx.
Перенос строки между fields.Xxx и первым аргументом строго запрещён.

Первый аргумент (selection=, string=, default= и т.д.) обязан находиться в той же строке, что и fields.Xxx(.

Каждый параметр:

размещается на отдельной строке,

имеет одинаковый отступ,

обязательно заканчивается запятой.

Закрывающая скобка ) и завершающая запятая , размещаются на отдельной строке.

Любое отклонение от данного формата считается ошибкой форматирования, даже если код синтаксически корректен.

✅ Эталонный (единственно допустимый) формат
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

❌ Запрещённый формат
import_state = fields.Selection(
    selection=[("not_imported", "Not Imported"),
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

Причина правила

Данный формат:

является каноническим стилем проекта SMK Constructor;

обеспечивает стабильные git-diff’ы;

легко машинно анализируется и генерируется;

предотвращает авто-реформатирование ИИ и IDE.

Обязательное указание для генераторов кода и ИИ

Запрещено переносить fields.Xxx( на новую строку.
Первый аргумент всегда должен находиться в той же строке.
### 8.2 Группировка полей по назначению

Поля в модели группируем блоками (логическими секциями), например:

- Technical / Import / State
- Manifest / Export
- UI helpers
- Relations
- Computed helpers

### 8.3 RU‑описание над каждым полем

Над каждым полем — комментарий RU (что это и зачем).

```python
# Состояние импорта (для UI и контроля актуальности данных)
import_state = fields.Selection(...)
```

---

## 9) Стиль процедур/методов (ВАШИ предпочтения — обязательны)

### 9.1 Разделитель секций

Любые большие смысловые блоки кода разделяем комментарием:

```python
# ================================
# Compute
# ================================
```

(точный маркер: строка с `===============` — обязателен)

### 9.2 Код максимально простой (middle‑level)

- без “магических” метапрограммных трюков
- без усложнений ради красоты
- читаемость важнее “умности”
- явные переменные, явные проверки, короткие функции
- сложное — выносим в `components/tools/` или в helper‑методы

---

## 10) Мини‑чеклист перед коммитом

- компонентная структура соблюдена (нет “плоских” `models/`/`views/` в корне)
- `tools/` не импортируется в `components/__init__.py`
- у каждого компонента есть свой `security/`
- у визардов есть свой `security/`
- `__manifest__.py` перечисляет все файлы явно и в нашем порядке
- поля оформлены многострочно + сгруппированы + RU‑комментарий над каждым
- секции методов разделены `===============`
- код читается “средним программистом” без расшифровки магии
