# 02_autolayout — ТЗ (авто-раскладка и запись данных)

## Назначение
Подпрограмма рассчитывает расположение блоков и, по настройкам, записывает вычислённые значения и/или дефолты в **файлы данных графа**. Результат — «канонический» файл для рендера.
Выходной файл создаётся **в той же папке**, что и входной, с суффиксом:
```
<name>.s02.autolayout.toml
```

## Размещение
```
02_autolayout/
  ├─ autolayout.py       # скрипт (будет создан позже)
  └─ config.toml         # конфигурация подпрограммы
```

## Вход/выход
- **Вход**: как правило, файлы `*.s01.prepared.toml` (или валидные исходники).
- **Выход**: `*.s02.autolayout.toml` рядом с входным файлом.

## Ключевые принципы
- Приоритет значений: **ручные** > **auto_*** > **defaults**.
- Заморозка (`freeze`) запрещает перезапись соответствующих групп данных.
- Запись обратно управляется **только новым форматом** `[[persist.groups]]` и `[persist.defaults]` (обратной совместимости нет).

## Алгоритм обработки
1. **Загрузка** TOML и конфигурации.
2. **Раскладка (layout)**:
   - режим `layered` (или `off`), направление `LR/RL/TB/BT`;
   - учёт `respect_fixed_blocks`: блоки с ручным `pos` не двигаем;
   - минимизация пересечений рёбер (эвристика), разведение коллизий;
   - вычисление `auto_pos` (и, опционально, `auto_width/auto_header_height/auto_prop_height`, если это разрешено).
3. **Очистка старых автополей**: перед записью удаляем `auto_*` прежних запусков (в текущем файле).
4. **Запись авто-данных в файл** согласно `[[persist.groups]]` и флагам `freeze`:
   - группы: `pos`, `size`, `shape`, `fonts`, `style`, `text`;
   - локальные `freeze_auto_*` у блока и глобальные `freeze` в `[[persist.groups]]` запрещают запись.
5. **Материализация дефолтов** `[persist.defaults]`:
   - `write = ["size"]` — переносит значения из `[defaults]` в **обычные поля блока** (`width`, `header_height`, `prop_height`);
   - `mode = "fill"` — только в пустые поля; `mode = "overwrite"` — перезаписывает ручные;
   - применяется **до** записи `auto_*`, чтобы далее действовали общие правила приоритетов/заморозок.
6. **Дедупликация `outs`** (на всякий случай) и финальная запись результата в `*.s02.autolayout.toml`.
7. **Отчёт**: что изменилось в каждом файле (см. ниже).

## Конфигурация `config.toml`
```toml
[io]
recursive = true
include_extensions = ["toml"]
include_globs = ["**/*.s01.prepared.toml", "**/*.toml"]
exclude_patterns = []
write_mode = "new"              # "new" | "inplace"
backup_original = false
dry_run = false
stop_on_error = true

[layout]
mode = "layered"                # "layered" | "off"
direction = "LR"                # LR | RL | TB | BT
minimize_edge_crossings = true
avoid_node_overlap = true
node_gap  = 0.08                # 0..1 (доля от канвы)
layer_gap = 0.12                # 0..1
respect_fixed_blocks = true

[defaults]
canvas_size = [1200, 800]
block.width = 0.10              # ← пример вашего кейса
block_header_height = 0.12
block_prop_height   = 0.10
# центровка по умолчанию
text_align_title  = "center"
text_align_props  = "center"
text_valign_title = "middle"
text_valign_props = "middle"

[persist]
# Новый формат, только он поддерживается
[[persist.groups]]
name   = "pos"
save   = true
freeze = false

[[persist.groups]]
name   = "size"
save   = true
freeze = false

# ... shape/fonts/style/text по необходимости

[persist.defaults]
# какие дефолты переносить в обычные поля блоков
write = ["size"]                # из defaults -> width/header_height/prop_height
mode  = "overwrite"             # "fill" | "overwrite"

[post]
dedupe_outs = true
```

## Отчёт
Для каждого файла:
- список блоков, чьи координаты/размеры были изменены (`auto_*` или материализованные `defaults`);
- отмеченные перезаписи ручных значений (если `mode="overwrite"`);
- предупреждения: недостающие цели `outs`, слишком малые/большие размеры, конфликтующие `freeze`.
Сводка: количество обновлённых файлов/блоков/стрелок.

## Ограничения
- Реализуемые типы кривых для рёбер: `"auto" | "straight" | "orthogonal"` (без spline).
- При `write_mode="inplace"` рекомендуется `backup_original=true`.
