python --version

поставить Python 3.10.12
https://www.python.org/downloads/windows/
![](Images\image8.png)
 
В пайчарме создать проект

![](Images\image2.png)

в Location записываем путь (например D:\Turbo_16) (папка заранеее создавать не нужно)

![](Images\image3.png)

в результате получится

![](Images\image4.png)

Создать папку Data из Пайчарма (например в папке venv)

Создать папку include из Пайчарма (обязательно в папке venv)
 
Распаковываешь базовую+энтерпрайз.

В папку include из Проводника скопироваить 2 директории (можно сразу всю директорию odoo16_bundle)


Делаешь гит клон, находясь в папке проекта
зайти на гит хаб

![](Images\image5.png)

(https://github.com/TURBO-UA/turbo.ua.git)

![](Images\image11.png)

![](Images\image6.png)

![](Images\image7.png)

(если по какой-то причине наши модули не попадут в проект, собери их в одну папку и тоже добавь в структуру проекта)


В odoo16.conf укажи все пути, как у тебя в проекте
(D:\Turbo_16\venv\include\odoo16.conf который шел в odoo16_bundle)

    в addons_path через запятую путь к папке адонс базовой оду 16, оду энтерпрайз и нашим кастомным
    в bin_path - путь в корень базовой оду 16
    в pg_path - путь к твоей папке bin постгреса

Зайти в корне базовой Оду 16 в файл requirements.txt. 

    Пайчарм должен предложить установить плагин (вверху синяя строка будет) - установи. 
    Он на основе рекомендаций найдёт нужные пакеты и подсветит лайны желтым, 
    при наведении появится попап, с предложением становить нужный пакет. 
    Пройдись по всем и поставь. (Там есть и поставить всё, но этот скрипт пропускает много паков).

    python.exe -m pip install --upgrade pip
    pip install -r D:\Turbo_16\venv\include\odoo-16.0\requirements.txt


Зайти к нашим кастомным моделям, там тоже лежит requirements.txt - повторить предыдущий пункт для этих пакетов

    pip install -r D:\Turbo_16\turbo.ua\requirements.txt  

Настроить конфиг пайчарма
    
    D:\Turbo_15\venv\include\odoo-15.0\odoo-bin
    -c "D:\Turbo_15\venv\include\odoo15.conf" -d turbo_15 --dev=all

![](Images\image12.png)

Изображение
Запустить. Зайти в http://localhost:8069/web/database/manager и сделать рестор БД (тут я думаю ты уже в курсе всей процедуры, если нет - могу расписать)


https://github.com/odoo/odoo


pip install pysftp

Ветка Гита - поставить Студио