# ТЗ / Master‑Prompt для подпрограммы 02_autolayout

## Назначение
Сгенерировать **auto_*** параметры (позиции, размеры, отступы, стили) и, при необходимости, материализовать значения по умолчанию в обычные поля.

## Вход / Выход
- **Вход**: файлы `*_01.toml` (результат 01_prepare).
- **Выход**: файлы `*_02.toml` в тех же папках.

## Конфигурация (config_autolayout.toml)
```toml
[io]
input_dirs = ["D:/Entertaiment/Графы/Пример 1"]
recursive = true
include_extensions = ["toml"]
exclude_patterns = ["*_02.toml", "*_03.toml"]
input_suffix = "_01.toml"
output_suffix = "_02"
write_mode = "new"
backup_original = false
dry_run = false
stop_on_error = true

[persist]
[[persist.groups]]  # pos
name = "pos"; save = true; freeze = false
[[persist.groups]]  # size
name = "size"; save = true; freeze = false
[[persist.groups]]  # shape
name = "shape"; save = true; freeze = false
[[persist.groups]]  # fonts
name = "fonts"; save = true; freeze = false
[[persist.groups]]  # text
name = "text"; save = true; freeze = false
[[persist.groups]]  # edge_style
name = "edge_style"; save = true; freeze = false

[persist.defaults]
materialize = []
mode = "fill"        # "fill" | "overwrite"

[layout]
mode = "layered"     # "layered" | "grid" | "off"
direction = "LR"     # "LR" | "RL" | "TB" | "BT"
node_gap = 0.10
layer_gap = 0.18
respect_fixed_blocks = true

[defaults]
canvas_size = [1200, 800]
block.width = 0.10
block.header_height = 0.10
block.prop_height   = 0.06
block.shape = "rounded"
block.corner_radius = 10.0
block.stroke_width  = 2.0
block.fill_color    = "none"
block.stroke_color  = "#000000"
font.family = "Arial"
font.size_title = 14
font.size_prop  = 12
font.bold_title = true
font.italic_arrow = true
block.text_align_title = "center"
block.text_align_props = "center"
block.text_valign_title = "middle"
block.text_valign_props = "middle"
block.text_padding_title_x = 6
block.text_padding_title_y = 6
block.text_padding_prop_x  = 6
block.text_padding_prop_y  = 6
theme.background = "#FFFFFF"
theme.text_color = "#000000"
theme.arrow_color = "#222222"
style.curve = "orthogonal"           # "auto"|"straight"|"orthogonal"
style.label_offset = 0.5
style.connector_from = "right"
style.connector_to   = "left"
```

## Обязательные преобразования
1. Рассчитать и записать `auto_*` по группам, указанным в `[[persist.groups]]`.
2. **Обязательно** преобразовать связи из старого формата в новый: `outs = [{to=..., label=...}]` и далее обеспечить, что в `[[blocks.outs]]` **всегда есть поле `label`** (пусть даже пустое).
3. По `persist.defaults.materialize`:
   - при `mode="fill"` — писать только в отсутствующие обычные поля;
   - при `mode="overwrite"` — заменить существующие значения.
4. Не выполнять рендер‑специфических операций.

## Нефункциональные требования
- Не трогать комментарии/форматирование, кроме собственных вставок ключей.
- Идемпотентность: повторный прогон не меняет файл (при одинаковых настройках).
- Логи: сколько блоков размещено, сколько рёбер обработано.

## Критерии приёмки
- Все блоки имеют согласованные `auto_pos`, `auto_width`, `auto_header_height`, `auto_prop_height` и т.п. согласно конфигу.
- В каждом `[[blocks.outs]]` присутствует `label` (строка, допускается пустая).

> **Важно для новых чатов:** не писать код, пока пользователь явно не попросит. Работать строго по этому ТЗ.
