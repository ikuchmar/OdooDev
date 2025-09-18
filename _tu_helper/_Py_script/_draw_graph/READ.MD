
# Техническое задание (финальная версия 1.2)

## 1. Назначение
Создать утилиту для визуализации графов процессов/структур, которая:  
- читает данные из TOML-файлов,  
- поддерживает составные блоки (заголовок + подблоки-свойства),  
- рисует направленные стрелки (от края к краю) с подписями,  
- выполняет авторасположение блоков с минимизацией пересечений стрелок,  
- сохраняет вычисленные координаты обратно в TOML,  
- работает с несколькими входными папками (рекурсивный поиск),  
- сохраняет PNG и SVG рядом с исходными данными,  
- по настройке открывает результат в браузере,  
- запускается без аргументов, используя `run.toml` для параметров.

## 2. Запуск
- Скрипт запускается без аргументов:  
  ```bash
  python _draw_graph.py
  ```  
- В той же папке ищется файл `run.toml`.  
- Отсутствие `run.toml` → ошибка с пояснением.

## 3. Формат `run.toml`
```toml
# Папки с графами
input_dirs = [
  "D:/Entertaiment/Английский/data/Урок 01",
  "D:/Проекты/Диаграммы"
]

# Обход подпапок
recursive = true

# Какие расширения обрабатывать
include_extensions = ["toml"]

# Исключения (глоб-паттерны)
exclude_patterns = ["*/_archive/*", "*_bak.toml"]

[layout]
mode = "layered"                 # off | force | layered
minimize_edge_crossings = true
avoid_node_overlap = true
edge_routing = "orthogonal"      # straight | orthogonal | spline | auto
edge_label_placement = "smart"
node_padding = 0.02
grid_snap = 0.01
deterministic = true
seed = 42

[persist]
write_positions_to_input = true
write_mode = "overwrite"         # update_missing | overwrite
sort_blocks = "by_pos_id"        # by_pos_id | by_id
sort_arrows = "by_from_to_label" # by_from_to_label | none
create_backup = true             # сохранять *.bak перед изменением

[output]
save_png = true
save_svg = true
png_dpi = 200
file_naming = "same_basename"    # X.toml → X.png / X.svg
open_in_browser = "svg"          # none | svg | html
show_preview_windows = false

[defaults]
canvas_size = [1000, 700]
style.curve = "auto"             # auto | straight | arc | spline
style.label_offset = 0.05
style.connector_from = "auto"    # auto | left | right | top | bottom
style.connector_to = "auto"      # auto | left | right | top | bottom
style.arrow_size = 1.0
style.arrow_thickness = 2.0

block.width = 0.35
block.header_height = 0.18
block.prop_height = 0.10
block.corner_radius = 10
block.stroke_width = 2.0
block.fill_color = "none"
block.stroke_color = "#000000"

font.family = "Arial"
font.size_title = 12
font.size_prop = 10
font.size_arrow = 9
font.bold_title = true
font.italic_arrow = true

theme.mode = "light"
theme.background = "#FFFFFF"
theme.text_color = "#000000"
theme.arrow_color = "#111111"
theme.block_fill_color = "none"
theme.block_stroke_color = "#000000"
```

## 4. Формат TOML данных графа
```toml
[global]
style.curve = "spline"
style.label_offset = 0.1
style.connector_from = "right"
style.connector_to = "left"

[meta]
title = "Название диаграммы"
canvas_size = [1200, 800]        # переопределяет defaults.canvas_size

[[blocks]]
id = "block1"
title = "Основной блок"
properties = ["Свойство 1", "Свойство 2"]
pos = [0.25, 0.60]               # нормированные координаты центра (0..1)
width = 0.35
header_height = 0.18
prop_height = 0.10

[[blocks]]
id = "block2"
title = "Другой блок"
properties = ["Атрибут A", "Атрибут B"]

[[arrows]]
from = "block1"
to = "block2"
label = "связь 1"

```

### Правила:
- `blocks[].id` — уникальные.  
- `arrows[].from` и `arrows[].to` — должны ссылаться на существующие блоки.  
- `pos` может отсутствовать: будет рассчитан авто-layout’ом.  
- Если `persist.write_positions_to_input=true` — итоговые `pos` записываются в файл.  
- При `write_mode="overwrite"` все позиции перезаписываются, при `update_missing` — только отсутствующие.  

## 5. Приоритет параметров
1. Явно указанный в файле графа (`diagram.toml`).  
2. Значение из `run.toml [defaults]`.  
3. Встроенное значение по умолчанию.  

Пример встроенных значений:
- `canvas_size = [800, 600]`
- `style.curve = "straight"`
- `block.width = 0.35`
- `theme.mode = "light"`
- `theme.background = "#FFFFFF"`

## 6. Логика работы
1. Прочитать `run.toml`.  
2. Собрать список входных TOML-файлов (`input_dirs`, `recursive`, `include_extensions`, `exclude_patterns`).  
3. Для каждого файла:  
   - Прочитать блоки и стрелки.  
   - Валидировать данные.  
   - Выполнить раскладку (`layout.mode`).  
   - Применить роутинг рёбер и размещение подписей.  
   - Сохранить позиции блоков в TOML (с бэкапом).  
   - Сгенерировать PNG и SVG.  
   - При `open_in_browser` — открыть SVG/HTML в браузере.  

## 7. Визуальные правила
- **Блоки**:  
  - рамка со скруглением (`block.corner_radius`),  
  - заголовок в шапке,  
  - свойства — подблоки одинаковой ширины.  
- **Стрелки**:  
  - направленные, от края к краю,  
  - стиль по `style.curve` и `layout.edge_routing`,  
  - подписи размещаются «умно» (`smart`) или по центру.  
- **Темы**:  
  - поддержка `light` и `dark`.  

## 8. Логи
- `OK: <file>` — успешная генерация.  
- `INFO: positions written` — позиции перезаписаны.  
- `WARN: overlap resolved` — блоки развели.  
- `WARN: label adjusted` — подпись сдвинута.  
- `ERROR: missing block id ...` — некорректные ссылки.  
- В конце: сводка (кол-во файлов, TOML изменённых, PNG/SVG создано, открытых в браузере).  

## 9. Критерии приёмки
- Запуск без аргументов, чтение `run.toml`.  
- Обработка всех подходящих файлов из `input_dirs`.  
- Авторасположение без наложений блоков.  
- Минимизация пересечений стрелок.  
- Позиции записываются обратно в TOML.  
- PNG и SVG создаются рядом с исходниками.  
- При `open_in_browser="svg"` результат открывается в браузере.  
- Детерминированность при одинаковом seed.  

## 10. Пограничные случаи
- Граф без стрелок — только блоки.  
- Длинные заголовки и подписи — переносятся, не накладываются.  
- Циклы и параллельные стрелки поддерживаются.  
- Пустые свойства в блоке — допустимо.  

## 11. Версионирование
- Версия ТЗ: **1.2**.  
- Возможные расширения: экспорты PDF, темы оформления, генерация легенд.  
