# Максимальный файл манифеста Odoo (`__manifest__.py`)

Документ описывает **максимально полный состав** файла манифеста модуля Odoo (версии 16–18, Community / Enterprise).

---

## 📄 Общая форма файла

```python
{
    # базовые метаданные
    # ------------------------------
    # Отображаемое имя модуля.
    'name': 'SMK Constructor',

    #  Короткое описание (1 строка)
    'summary': 'Visual constructor for Odoo modules',

    # Полное описание (можно многострочное)
    'description': """
    Module builder similar to 1C configurator.
    - Models
    - Fields
    - Views
    """,
    # Формат: 18.0.1.0.0,  17.0.2.3
    'version': '18.0.1.0.0',

    # Информация об авторе
    # ------------------------------
    'author': 'SMK',
    'website': 'https://smk.company',

    # Часто используемые лицензии: LGPL-3, OPL-1, OEEL-1, MIT
    'license': 'LGPL-3',

    # Определяет раздел в Apps Примеры: Tools, Technical, Sales, Human, Resources, Hidden
    'category': 'Tools',

    # Порядок отображения
    'sequence': 10,

    # зависимости и установка
    # ------------------------------
    'depends': [
        'base',
        'web',
        'mail',
    ],

    # Для Python / system-lib зависимостей
    'external_dependencies': {
        'python': ['lxml', 'Pillow'],
        'bin': ['ffmpeg'],
    },

    # данные и ресурсы 
    # ------------------------------
    # Загружается всегда
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/menu.xml',
        'views/model_views.xml',
        'views/actions.xml',
        'data/constructor_type_data.xml',
    ],

    # Загружается только при demo=True
    'demo': [
        'demo/demo_data.xml',
    ],
    # Assets (JS / CSS / SCSS / XML)
    # ------------------------------
    # Ключевые бандлы: web.assets_backend  web.assets_frontend  web.assets_common web.qunit_suite_tests
    'assets': {
        'web.assets_backend': [
            'smk_constructor/static/src/js/**/*.js',
            'smk_constructor/static/src/xml/**/*.xml',
            'smk_constructor/static/src/scss/**/*.scss',
        ],
        'web.assets_frontend': [
            'smk_constructor/static/src/css/frontend.css',
        ],
    },

    # поведение модуля
    # ------------------------------
    # Можно ли установить
    'installable': True,
    'application': False,
    'auto_install': False,

    # хуки и инициализация
    # ------------------------------
    'pre_init_hook': '',
    'post_init_hook': '',
    'uninstall_hook': '',

    # прочее
    # ------------------------------
    'images': [],
    'price': 0.0,
    'currency': '',
    'maintainers': [],
}
```

---

## 1️⃣ Базовые метаданные

### `name`
Отображаемое имя модуля.
```python
'name': 'SMK Constructor',
```

### `summary`
Краткое описание (1 строка).
```python
'summary': 'Visual constructor for Odoo modules',
```

### `description`
Полное описание (поддерживает многострочный текст).
```python
'description': '''
Module builder similar to 1C configurator.
- Models
- Fields
- Views
''',
```

### `version`
Рекомендуемый формат:
- `18.0.1.0.0`
- `17.0.2.3`
```python
'version': '18.0.1.0.0',
```

---

## 2️⃣ Автор и лицензия

```python
'author': 'SMK',
'website': 'https://smk.company',
'license': 'LGPL-3',
```

Популярные лицензии:
- LGPL-3
- OPL-1
- OEEL-1
- MIT

---

## 3️⃣ Категория и порядок

### `category`
Раздел в Apps.
```python
'category': 'Tools',
```

### `sequence`
Порядок отображения.
```python
'sequence': 10,
```

---

## 4️⃣ Зависимости

### `depends`
Критически важный параметр.
```python
'depends': ['base', 'web', 'mail'],
```

### `external_dependencies`
Системные и python-зависимости.
```python
'external_dependencies': {
    'python': ['lxml', 'Pillow'],
    'bin': ['ffmpeg'],
},
```

---

## 5️⃣ Данные

### `data`
Загружаются всегда.
```python
'data': [
    'security/ir.model.access.csv',
    'views/menu.xml',
    'views/actions.xml',
],
```

### `demo`
Загружаются только в demo-режиме.
```python
'demo': [
    'demo/demo_data.xml',
],
```

---

## 6️⃣ Assets

```python
'assets': {
    'web.assets_backend': [
        'module/static/src/js/**/*.js',
        'module/static/src/xml/**/*.xml',
        'module/static/src/scss/**/*.scss',
    ],
    'web.assets_frontend': [
        'module/static/src/css/frontend.css',
    ],
},
```

Доступные бандлы:
- web.assets_backend
- web.assets_frontend
- web.assets_common
- web.qunit_suite_tests

---

## 7️⃣ Поведение модуля

```python
'installable': True,
'application': False,
'auto_install': False,
```

---

## 8️⃣ Хуки

```python
'pre_init_hook': 'pre_init_hook',
'post_init_hook': 'post_init_hook',
'uninstall_hook': 'uninstall_hook',
```

Используются для:
- миграций
- инициализации
- очистки при удалении

---

## 9️⃣ Изображения и маркетинг

```python
'images': [
    'static/description/banner.png',
],
```

### Цена (Marketplace)
```python
'price': 49.99,
'currency': 'EUR',
```

---

## 🔟 Maintainers

```python
'maintainers': ['smk'],
```

---

## 🧠 Логическая структура

```
manifest
├── metadata
├── author & license
├── category & ui
├── dependencies
├── data / demo
├── assets
├── hooks
├── install behavior
└── marketing
```

---

Документ подходит как:
- reference
- шаблон для генерации манифестов
- база для конструктора модулей Odoo
