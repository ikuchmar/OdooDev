# ТЗ / Master‑Prompt для подпрограммы 03_render

## Назначение
Построить финальный SVG по уже рассчитанным данным. Никаких вычислений `auto_*` на этом этапе.

## Вход / Выход
- **Вход**: файлы `*_02.toml` (результат 02_autolayout).
- **Выход**: файлы `*_03.svg` рядом с входными.

## Конфигурация (config_render.toml)
```toml
[io]
input_dirs = ["D:/Entertaiment/Графы/Пример 1"]
recursive = true
include_extensions = ["toml"]
exclude_patterns = []
input_suffix = "_02.toml"
output_suffix = "_03"       # будет flow.graph_01_02_03.svg
write_mode = "new"
backup_original = false
dry_run = false
stop_on_error = true

[output]
open_after_render = true     # открыть SVG в браузере по завершении

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
block.props_dividers = true
block.props_divider_thickness = 1.0
```

## Правила отрисовки
1. **Рёбра**: выход из **правого края** источника, вход в **левый край** цели (`connector_from="right"`, `connector_to="left"`). Не рисовать «центр‑в‑центр`.
2. **Свойства блока**: между строками рисовать горизонтальные разделители, а также разделитель между заголовком и первой строкой.
3. Все размеры и позиции брать из данных/`auto_*`, **не вычислять** их заново.
4. Цвета/шрифты — из входного файла или из `[defaults]` как из дефолтов.

## Критерии приёмки
- SVG открывается в браузере и визуально совпадает с эталонной схемой (с правыми/левыми коннекторами).
- Все свойства читаемы; разделители присутствуют.

> **Важно для новых чатов:** не писать код, пока пользователь явно не попросит. Работать строго по этому ТЗ.
