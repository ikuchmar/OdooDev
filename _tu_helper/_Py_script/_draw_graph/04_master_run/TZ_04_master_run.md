# ТЗ / Master‑Prompt для подпрограммы 04_master_run (оркестратор)

## Назначение
Запускать конвейер (01 → 02 → 03) по шагам, **безопасно** внося правки в конфигурации подскриптов.

## Ключевые требования
- **Безопасная правка TOML**: точечная вставка `key = value` в нужную секцию, **с сохранением комментариев и форматирования**. Никакой полной перезаписи.
- **.bak** создавать **только если файл реально меняется**.
- Поиск скриптов по структуре проекта `_draw_graph/01_prepare|02_autolayout|03_render|04_master_run`.
- Поддержка шагов: `set_params`, `run_script`, `set_params_and_run`.
- Поддержка опций: `dry_run`, `continue_on_error`, `backup_configs`, `python_executable`.
- Очистка промежуточных файлов, если `[globals].delete_toml_after=true`:
  - после успешного `autolayout.py` удалить `*_01.toml`;
  - после `render.py` удалить `*_02.toml`.

## Конфигурация (config_master_run.toml) — схема
```toml
[globals]
input_dirs = ["D:/Entertaiment/Графы/Пример 1"]
delete_toml_after = true

[options]
dry_run = false
continue_on_error = false
backup_configs = true
python_executable = ""

[[steps]]                      # Пример 01_prepare
type = "set_params_and_run"
targets = ["01_prepare/config_prepare.toml"]
  [[steps.params]]
  key = "io.input_dirs"
  use = "global"
  global_key = "input_dirs"
  [[steps.params]]
  key = "io.input_suffix"
  use = "value"
  value = ".toml"
  [[steps.params]]
  key = "io.output_suffix"
  use = "value"
  value = "_01"
  [[steps.params]]
  key = "io.exclude_patterns"
  use = "value"
  value = ["*_01.toml", "*_02.toml", "*_03.toml"]
  [steps.run]
  script = "01_prepare/prepare.py"
  args = []

# Аналогично для 02_autolayout и 03_render (сменить input/output_suffix и параметры)
```

## Нефункциональные
- Печатать понятные логи (что меняем, что запускаем).
- При ошибке — код возврата ≠ 0 (если `continue_on_error=false`).
- Не склеивать секции; гарантировать перевод строки в конце файла после правки.

## Критерии приёмки
- Шаги 01→02→03 успешно выполняются в правильном порядке.
- Конфиги подправляются только в указанных ключах; комментарии и форматирование сохранены.
- .bak создаётся только при фактическом изменении файла.

> **Важно для новых чатов:** не писать код, пока пользователь явно не попросит. Работать строго по этому ТЗ.
