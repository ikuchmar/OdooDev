Проект для автоматической отрисовки блок-схем из TOML-файлов с поддержкой ручной фиксации параметров и авто-генерации «умолчаний».

1) Назначение

draw_graph.py считывает описание диаграммы в формате TOML, раскладывает блоки слоями (направление слева→направо по умолчанию), строит стрелки и сохраняет результат в SVG/PNG. Ручные параметры узлов уважаются, авто-параметры пересчитываются при каждом запуске и (по настройке) могут записываться обратно в файл диаграммы.

2) Структура проекта
/_draw_graph/
  draw_graph.py         # Скрипт отрисовки
  run.toml              # Глобальная конфигурация
  flow.graph.toml       # Пример диаграммы
  output/               # Сохранённые SVG/PNG


Пример «графа»: flow.graph.toml — показывает формат [[blocks]] и вложенные [[blocks.outs]] (исходящие связи).

Конфигурация: run.toml — все параметры с комментариями и дефолтами.

3) Установка и требования

Python 3.11+ (рекомендуется 3.12)

Для PNG-экспорта нужен cairosvg (опционально)

Шрифты: используется системный шрифт из font.family (по умолчанию — Arial).

pip install cairosvg  # только если нужен PNG

4) Запуск
python draw_graph.py


Скрипт рекурсивно ищет входные TOML в директориях input_dirs, фильтрует по include_extensions и строит для каждого найденного файла.

5) Конфигурация (run.toml)
5.1 Поиск входных файлов

input_dirs: список папок; recursive: true|false; include_extensions; exclude_patterns.

5.2 Раскладка (layout)

layout.mode: "layered" (слоями) или "off" (использовать pos/auto_pos как есть).

layout.direction: "LR"|"RL"|"TB"|"BT"; по умолчанию — "LR" (слева→направо).

minimize_edge_crossings: bool — снижать пересечения рёбер; avoid_node_overlap: bool — разводить пересечения блоков.

Отступы: node_gap — зазор между соседями в слое; layer_gap — зазор между слоями (0..1).

respect_fixed_blocks: bool — если у блока есть ручной pos=[x,y], раскладка его не двигает.

Прочее: grid_snap (привязка к сетке при записи позиций), deterministic, seed.

5.3 Сохранение авто-параметров

[persist].create_backup: делать .bak перед перезаписью.

[persist].persist_auto_fields: какие группы auto_* записывать назад в [[blocks]] — "pos", "size", "shape", "fonts", "style", "text".

freeze_auto_*: bool — заморозка групп (не перезаписывать соответствующие auto_*).

5.4 Вывод

[output].save_svg: bool, [output].save_png: bool, png_dpi, open_in_browser: "svg"|"none".

5.5 Значения по умолчанию (defaults)

canvas_size = [W,H] в пикселях.

Размеры блока (нормированные, 0..1):
block.width, block.header_height, block.prop_height.

Форма и стиль: block.shape ("rect"|"rounded"|"pill"|"ellipse"), block.corner_radius, block.stroke_width, block.fill_color, block.stroke_color.

Шрифты: font.family, font.size_title, font.size_prop, font.bold_title, font.italic_arrow.

Текст в блоках:
block.text_align_title|props ("left"|"center"|"right"),
block.text_valign_title|props ("baseline"|"middle"),
block.text_padding_* (px).

Стрелки по умолчанию: style.curve ("auto"|"straight"|"orthogonal"|"spline"), style.label_offset (0..1), style.connector_from|to ("auto"|"left"|"right"|"top"|"bottom"), style.arrow_size, style.arrow_thickness.

6) Формат файла диаграммы (TOML)
6.1 Заголовок
[meta]
title = "Пример диаграммы"
canvas_size = [1200, 800]  # опционально, перекрывает defaults


6.2 Блоки
[[blocks]]
id = "block9"
title = "Старт"
properties = ["Инициализация", "Параметры"]


properties — имена подблоков-свойств. Высота каждой строки берётся из block.prop_height (или auto_prop_height).

6.2.1 Ручная фиксация размеров/позиции

Если задать ручные поля, они «уважаются» и раскладка их не трогает:

pos = [0.25, 0.60]         # нормированные координаты центра (0..1)
width = 0.35               # нормированная ширина
header_height = 0.18       # высота заголовка (норм.)
prop_height = 0.10         # высота ОДНОГО свойства (норм.)


(соответствует логике respect_fixed_blocks = true и приоритету ручных параметров).

6.2.2 Авто-параметры (пересчитываются каждый запуск)

Скрипт генерирует и может сохранять обратно поля auto_*:

auto_pos = [0.13, 0.50]
auto_width = 0.22
auto_header_height = 0.12
auto_prop_height = 0.06
auto_shape = "rounded"
auto_corner_radius = 10
auto_stroke_width = 2
auto_fill  = "none"
auto_stroke = "#000000"
auto_font_family = "Arial"
auto_font_size_title = 14
auto_font_size_prop  = 12
auto_font_bold_title = true
auto_font_italic_arrow = true
auto_text_align_title = "center"
auto_text_align_props = "left"
auto_text_valign_title = "baseline"
auto_text_valign_props = "baseline"
auto_text_padding_title_x = 6
auto_text_padding_title_y = 6
auto_text_padding_prop_x  = 6
auto_text_padding_prop_y  = 6


Перечень отражает группы pos/size/shape/fonts/style/text из [persist].persist_auto_fields.

Важно: перед построением скрипт очищает старые auto_* (чтобы не копились) и генерирует их заново из актуальных настроек run.toml. При наличии ручного аналога (pos, width, ...), ручное значение имеет приоритет, а auto_* корректируется только там, где ручного нет. (Поведение контроля записи/заморозки см. §5.3.)

6.3 Связи (стрелки) внутри блока

Исходящие стрелки задаются вложенными таблицами у блока:

[[blocks.outs]]
to = "block2"
label = "go"               # подпись (опц.)
style.curve = "orthogonal" # перегрузка дефолтов для ребра (опц.)
style.label_offset = 0.5   # 0..1, 0.5 — по центру
style.connector_from = "right"
style.connector_to   = "left"


Формат [[blocks.outs]] полностью заменил старые [[arrows]] и сокращённый синтаксис outs = ["B", ...]. При обнаружении устаревших записей скрипт преобразует их в новый вложенный формат.

7) Алгоритм приоритета параметров

Для каждого блока и каждой настройки:

Если задано ручное поле (например, width, pos, header_height, prop_height, выравнивание/шрифты/форма) — использовать его.

Иначе, если есть актуальное auto_* (после пересчёта) — использовать его.

Иначе — взять дефолт из [defaults] в run.toml.

Запись auto_* назад в [[blocks]] управляется [persist] и флажками freeze_auto_*.

8) Текст и выравнивание

Горизонталь: left|center|right → SVG text-anchor="start|middle|end". По умолчанию заголовок по центру, свойства — по центру/слева (смотри текущие дефолты в run.toml).

Вертикаль: baseline|middle. Для одиночных строк удобно middle (вертикальный центр строки). Дефолты можно переопределить в defaults.

Отступы текста задаются в пикселях (block.text_padding_*).

9) Стрелки

Кривая: style.curve = "auto"|"straight"|"orthogonal"|"spline".

Подпись на ребре: style.label_offset = 0..1 — 0.5 ставит подпись по центру.

Подключения к сторонам блоков: style.connector_from|to = "auto"|"left"|"right"|"top"|"bottom".

Размер наконечника и толщина — style.arrow_size, style.arrow_thickness.
Все значения можно задать глобально в run.toml и адресно в каждом [[blocks.outs]].

10) Направление и слои

По умолчанию схема строится слева направо (layout.direction = "LR"). Можно выбрать и другие ориентации: RL, TB, BT. Раскладка «слоями» создаёт ряды блоков с контролем зазоров и попыткой уменьшить пересечения.

11) Экспорт

SVG всегда точный и масштабируемый ([output].save_svg = true).

PNG зависит от установленного cairosvg; плотность задаётся png_dpi.

Можно авто-открывать SVG после генерации: open_in_browser = "svg".

12) Обратная запись и безопасность данных

Перед перезаписью исходника может создаваться .bak (включено по умолчанию).

Во избежание «разрастания» файла, скрипт очищает прежние auto_* и пишет только актуальные, согласно persist_auto_fields и freeze_auto_*.

13) Пример минимальной диаграммы
[meta]
title = "Пример диаграммы"

[[blocks]]
id = "A"
title = "Старт"
properties = ["Инициализация", "Параметры"]

[[blocks.outs]]
to = "B"
label = "go"
style.curve = "orthogonal"
style.connector_from = "right"
style.connector_to   = "left"

[[blocks]]
id = "B"
title = "Обработка"
properties = ["Верификация", "Фильтрация", "Агрегация"]

[[blocks.outs]]
to = "C"
label = "finish"

[[blocks]]
id = "C"
title = "Завершение"
properties = ["Финал"]


(Подробный пример со сгенерированными auto_* см. в flow.graph.toml.)

14) Известные моменты и рекомендации

Если вручную заданы pos/width/header_height/prop_height, включите respect_fixed_blocks = true, чтобы раскладка не смещала такие блоки.

При миграции со старого формата ([[arrows]], outs=[...]) дайте скрипту пройтись по файлу — он преобразует в [[blocks.outs]]. Проверьте дубликаты исходящих связей (в ранних версиях они могли накапливаться).

Для центрирования подписи ребра используйте style.label_offset = 0.5.

15) История изменений (TL;DR)

Перешли на формат [[blocks.outs]] (вместо [[arrows]] и outs=[...]).

Добавлен расширенный набор auto_* для формы/шрифтов/стилей/текста с управлением группами через [persist].

Поддержка вертикального центрирования текста — через block.text_valign_* = "middle".

Направление раскладки по умолчанию — LR (слева→направо).