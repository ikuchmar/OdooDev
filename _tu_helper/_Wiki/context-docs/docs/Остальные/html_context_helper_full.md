==========================
## html-overview
==========================
HTML - Обзор - Навигация
--------------------------------------------
Навигатор по HTML для контекстного помощника. Ищи нужную секцию по ключу.
Секции сгруппированы: структура, текст, списки, ссылки/медиа, таблицы, формы, семантика, встраивание, служебные теги, доступность (ARIA), SEO/метаданные, производительность.
```md
**Структура:** `doctype`, `html`, `head`, `meta`, `title`, `link`, `style`, `script`, `base`, `body`  
**Текст:** `headings`, `p`, `br`, `hr`, `strong-em-b-i-u-mark-small`, `sup-sub`, `code-pre`, `q-cite-blockquote`, `abbr-dfn`, `kbd-samp-var`, `span-div`  
**Списки:** `ul-ol-li`, `dl-dt-dd`  
**Ссылки/медиа:** `a`, `img`, `picture`, `figure-figcaption`, `audio-video`, `source-track`, `map-area`  
**Таблицы:** `table`, `thead-tbody-tfoot`, `tr-th-td`, `caption`, `colgroup-col`  
**Формы:** `form`, `label-input`, `input-types`, `textarea`, `select-option-optgroup`, `button`, `fieldset-legend`, `datalist-output`, `progress-meter`, `form-validation`, `autocomplete-pattern`  
**Семантика:** `semantic-layout`, `main-section-article`, `aside`, `header-footer`, `nav-breadcrumbs`, `time-address`, `details-summary`, `dialog`  
**Встраивание/графика:** `iframe`, `embed-object-param`, `canvas`, `svg`  
**Служебные:** `template-slot`, `noscript`, `meta-viewport-favicons`, `opengraph-twitter`, `preload-prefetch`, `defer-async-module`, `loading-fetchpriority`  
**Доступность:** `aria-overview`, `aria-landmarks`, `aria-controls-live`  
**Глобальные атрибуты:** `global-attrs`  
**Практики:** `performance-best`, `security-best`, `forms-best`, `images-best`
```

==========================
## doctype
==========================
HTML - Базовые теги - Структура документа
--------------------------------------------
Объявление стандарта HTML5. Всегда самое первое в документе.
```html
<!DOCTYPE html>
```

==========================
## html
==========================
HTML - Базовые теги - Структура документа
--------------------------------------------
Корневой элемент. Атрибут `lang` задаёт язык контента, важен для доступности и SEO.
```html
<!DOCTYPE html>
<html lang="ru">
  ...
</html>
```

==========================
## head
==========================
HTML - Базовые теги - Структура документа
--------------------------------------------
Служебная часть: метаданные, подключения, заголовок. Не содержит видимого контента страницы.
```html
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Название страницы</title>
  <link rel="stylesheet" href="/assets/site.css">
  <script src="/assets/app.js" defer></script>
</head>
```

==========================
## meta
==========================
HTML - Базовые теги - Метаданные
--------------------------------------------
Метаданные документа. Частые: кодировка, viewport, описание, автор, robots.
```html
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Краткое описание страницы">
<meta name="robots" content="index, follow">
<meta name="author" content="Igor">
```

==========================
## title
==========================
HTML - Базовые теги - Метаданные
--------------------------------------------
Заголовок документа во вкладке браузера. Один на документ.
```html
<title>Моя страница</title>
```

==========================
## link
==========================
HTML - Базовые теги - Подключения
--------------------------------------------
Подключение внешних ресурсов: стили, иконки, preconnect, prefetch и др.
```html
<link rel="stylesheet" href="/css/styles.css">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="dns-prefetch" href="//example.cdn.com">
```

==========================
## style
==========================
HTML - Базовые теги - Подключения
--------------------------------------------
Встраивание CSS прямо в документ. Для крупных проектов предпочитай внешние файлы.
```html
<style>
  :root { --brand: #5b8def; }
  body { font-family: system-ui, sans-serif; }
</style>
```

==========================
## script
==========================
HTML - Базовые теги - Подключения
--------------------------------------------
Подключение JavaScript. `defer` — запуск после парсинга, `async` — независимо от парсинга, `type="module"` — ES-модули.
```html
<script src="/js/app.js" defer></script>
<script async src="https://example.com/ads.js"></script>
<script type="module">
  import { init } from '/js/module.js';
  init();
</script>
```

==========================
## base
==========================
HTML - Базовые теги - Подключения
--------------------------------------------
`base` задаёт базовый URL для относительных ссылок и таргет по умолчанию. Должен быть один и в `<head>`.
```html
<head>
  <base href="https://example.com/subdir/" target="_blank">
</head>
```

==========================
## body
==========================
HTML - Базовые теги - Структура документа
--------------------------------------------
Видимое содержимое страницы: заголовки, тексты, секции, изображения и т.д.
```html
<body>
  <h1>Заголовок</h1>
  <p>Контент...</p>
</body>
```

==========================
## headings
==========================
HTML - Текст - Заголовки
--------------------------------------------
`h1`–`h6`: иерархия разделов. Обычно `h1` — один на страницу.
```html
<h1>Главный</h1>
<h2>Раздел</h2>
<h3>Подраздел</h3>
```

==========================
## p
==========================
HTML - Текст - Базовое
--------------------------------------------
Абзац текста. Не допускается вложение блочных элементов внутрь `p`.
```html
<p>Это абзац текста.</p>
```

==========================
## br-hr
==========================
HTML - Текст - Разделители
--------------------------------------------
`br` — перенос строки. `hr` — тематический разрыв.
```html
Первая строка<br>Вторая строка
<hr>
После разделителя
```

==========================
## strong-em-b-i-u-mark-small
==========================
HTML - Текст - Выделение
--------------------------------------------
`strong` и `em` — логическое выделение (важность/акцент). `b/i` — визуальное. `u` — подчёркивание, `mark` — подсветка, `small` — менее важный текст.
```html
<p>
  <strong>Важно</strong>, <em>акцент</em>,
  <b>жирно</b>, <i>курсив</i>,
  <u>подчёркнуто</u>, <mark>подсветка</mark>,
  <small>сноска</small>
</p>
```

==========================
## sup-sub
==========================
HTML - Текст - Индексы
--------------------------------------------
Надстрочный (`sup`) и подстрочный (`sub`) текст.
```html
E = mc<sup>2</sup>, H<sub>2</sub>O
```

==========================
## code-pre
==========================
HTML - Текст - Код
--------------------------------------------
`code` — фрагмент кода, `pre` — сохранение форматирования.
```html
<pre><code>const x = 42;
console.log(x);
</code></pre>
```

==========================
## q-cite-blockquote
==========================
HTML - Текст - Цитаты
--------------------------------------------
`q` — краткая цитата (встроенная), `blockquote` — блочная цитата. Атрибут `cite` ссылается на источник.
```html
<p>Как сказал Н.: <q cite="https://example.com">Короткая цитата</q></p>
<blockquote cite="https://example.com/article">
  Длинная цитата...
</blockquote>
```

==========================
## abbr-dfn
==========================
HTML - Текст - Термины
--------------------------------------------
`abbr` — аббревиатуры (title — расшифровка), `dfn` — термин, определяемый в тексте.
```html
<p><abbr title="Application Programming Interface">API</abbr></p>
<p><dfn>Вьюпорт</dfn> — область экрана для отображения страницы.</p>
```

==========================
## kbd-samp-var
==========================
HTML - Текст - Спец. обозначения
--------------------------------------------
`kbd` — ввод с клавиатуры, `samp` — вывод программы, `var` — переменная.
```html
<p>Нажмите <kbd>Ctrl</kbd> + <kbd>S</kbd></p>
<p>Ответ: <samp>OK</samp></p>
<p><var>x</var> = 10</p>
```

==========================
## span-div
==========================
HTML - Контейнеры - Строчный и Блочный
--------------------------------------------
`span` — строчный контейнер, `div` — блочный контейнер для группировки.
```html
<p>Текст со <span class="hl">строчным</span> фрагментом.</p>
<div class="card">...</div>
```

==========================
## ul-ol-li
==========================
HTML - Списки - Маркированные и Нумерованные
--------------------------------------------
`ul` — маркированный, `ol` — нумерованный, `li` — пункт. Вложенность разрешена.
```html
<ul><li>HTML</li><li>CSS</li></ul>
<ol><li>Шаг 1</li><li>Шаг 2</li></ol>
```

==========================
## dl-dt-dd
==========================
HTML - Списки - Список определений
--------------------------------------------
`dl` — список определений, `dt` — термин, `dd` — определение.
```html
<dl>
  <dt>HTML</dt>
  <dd>Язык разметки</dd>
</dl>
```

==========================
## a
==========================
HTML - Ссылки и медиа - Ссылки
--------------------------------------------
Гиперссылка. Атрибуты: `href`, `target`, `rel`. Для `_blank` — `rel="noopener noreferrer"`.
```html
<a href="/about.html">О нас</a>
<a href="https://example.com" target="_blank" rel="noopener noreferrer">Внешняя</a>
<a href="#contact">К контактам</a>
```

==========================
## img
==========================
HTML - Ссылки и медиа - Изображения
--------------------------------------------
Изображение. Обязателен `alt`. Поддерживаются атрибуты `width`, `height`, `loading`, `decoding`, `fetchpriority`.
```html
<img src="/img/photo.jpg" alt="Пейзаж" width="800" height="600" loading="lazy" decoding="async" fetchpriority="low">
```
```css
img { max-width: 100%; height: auto; }
```

==========================
## picture
==========================
HTML - Ссылки и медиа - Адаптивные изображения
--------------------------------------------
`picture` + `source` подбирают формат/размер под устройство.
```html
<picture>
  <source srcset="img.avif" type="image/avif">
  <source srcset="img.webp" type="image/webp">
  <img src="img.jpg" alt="Описание">
</picture>
```

==========================
## figure-figcaption
==========================
HTML - Ссылки и медиа - Иллюстрации
--------------------------------------------
`figure` — самостоятельный блок, `figcaption` — подпись.
```html
<figure>
  <img src="chart.png" alt="Диаграмма">
  <figcaption>Диаграмма продаж</figcaption>
</figure>
```

==========================
## audio-video
==========================
HTML - Ссылки и медиа - Медиа
--------------------------------------------
Встроенные медиа. `controls`, `autoplay`, `muted`, `loop`, `poster` (для видео).
```html
<audio controls>
  <source src="music.ogg" type="audio/ogg">
  <source src="music.mp3" type="audio/mpeg">
</audio>

<video controls width="640" height="360" poster="preview.jpg">
  <source src="video.webm" type="video/webm">
  <source src="video.mp4" type="video/mp4">
</video>
```

==========================
## source-track
==========================
HTML - Ссылки и медиа - Источники/субтитры
--------------------------------------------
`source` — альтернативные источники. `track` — субтитры/описания.
```html
<video controls>
  <source src="movie.mp4" type="video/mp4">
  <track kind="subtitles" src="subs.vtt" srclang="ru" label="Русские">
</video>
```

==========================
## map-area
==========================
HTML - Ссылки и медиа - Карты изображений
--------------------------------------------
Кликабельные области на изображении через `usemap`, `map`, `area`.
```html
<img src="plan.png" alt="План" usemap="#m">
<map name="m">
  <area shape="rect" coords="10,10,120,80" href="/room/1" alt="Комната 1">
</map>
```

==========================
## table
==========================
HTML - Таблицы - Базовое
--------------------------------------------
Таблица; используйте семантические блоки и подписи.
```html
<table>
  <caption>Прайс-лист</caption>
  ...
</table>
```

==========================
## thead-tbody-tfoot
==========================
HTML - Таблицы - Структура
--------------------------------------------
Секции таблицы: заголовок, тело, подвал.
```html
<table>
  <thead><tr><th>Товар</th><th>Цена</th></tr></thead>
  <tbody><tr><td>Ручка</td><td>20</td></tr></tbody>
  <tfoot><tr><td>Итого</td><td>20</td></tr></tfoot>
</table>
```

==========================
## tr-th-td
==========================
HTML - Таблицы - Ячейки
--------------------------------------------
`tr` — строка, `th` — заголовочная ячейка, `td` — обычная ячейка. Атрибуты `scope`, `rowspan`, `colspan`.
```html
<tr>
  <th scope="col">Имя</th>
  <td>Иван</td>
</tr>
```

==========================
## caption
==========================
HTML - Таблицы - Подпись
--------------------------------------------
Описание таблицы. Обычно первым дочерним элементом `table`.
```html
<table>
  <caption>Статистика</caption>
  ...
</table>
```

==========================
## colgroup-col
==========================
HTML - Таблицы - Колонки
--------------------------------------------
Стилизация/ширины колонок целиком.
```html
<table>
  <colgroup>
    <col style="width:70%">
    <col style="width:30%">
  </colgroup>
  ...
</table>
```

==========================
## form
==========================
HTML - Формы - Базовое
--------------------------------------------
Контейнер формы. `action`, `method` (`get`/`post`), `enctype`, `novalidate`.
```html
<form action="/submit" method="post">
  ...
</form>
```

==========================
## label-input
==========================
HTML - Формы - Метки и поля
--------------------------------------------
`label` связывается с `input` по `for`/`id` или оборачивает поле.
```html
<label for="email">Email</label>
<input type="email" id="email" name="email" required>
```

==========================
## input-types
==========================
HTML - Формы - Типы input
--------------------------------------------
Частые типы: text, email, password, number, tel, url, search, date, time, datetime-local, month, week, color, range, file, checkbox, radio, hidden, submit, reset, button.
```html
<input type="text">
<input type="number" min="0" max="10" step="1">
<input type="date">
<input type="checkbox"> Я согласен
<input type="radio" name="g" value="a"> A
```

==========================
## textarea
==========================
HTML - Формы - Поля
--------------------------------------------
Многострочное поле. Атрибуты: `rows`, `cols`, `maxlength`, `placeholder`.
```html
<textarea rows="4" placeholder="Введите комментарий..."></textarea>
```

==========================
## select-option-optgroup
==========================
HTML - Формы - Выбор
--------------------------------------------
`select` — список, `option` — пункт, `optgroup` — группа.
```html
<select>
  <optgroup label="UA">
    <option>Київ</option>
  </optgroup>
  <optgroup label="PL">
    <option>Краків</option>
  </optgroup>
</select>
```

==========================
## button
==========================
HTML - Формы - Кнопки
--------------------------------------------
Типы: `button` (по умолчанию), `submit`, `reset`.
```html
<button type="submit">Отправить</button>
<button type="button">Кнопка</button>
```

==========================
## fieldset-legend
==========================
HTML - Формы - Группировка
--------------------------------------------
`fieldset` группирует поля, `legend` — подпись группы.
```html
<fieldset>
  <legend>Контакты</legend>
  <label>Имя <input type="text"></label>
</fieldset>
```

==========================
## datalist-output
==========================
HTML - Формы - Дополнительно
--------------------------------------------
`datalist` — список подсказок для `input[list]`. `output` — результат вычислений формы.
```html
<input list="browsers"><datalist id="browsers"><option>Chrome</option></datalist>
<output name="total">0</output>
```

==========================
## progress-meter
==========================
HTML - Формы - Индикаторы
--------------------------------------------
`progress` — индикатор прогресса, `meter` — шкала величины в диапазоне.
```html
<progress value="30" max="100"></progress>
<meter min="0" max="100" low="30" high="70" optimum="80" value="65"></meter>
```

==========================
## form-validation
==========================
HTML - Формы - Валидация
--------------------------------------------
HTML5-валидация: `required`, `min`, `max`, `pattern`, `minlength`, `maxlength`, `step`.
```html
<input type="email" required>
<input type="text" pattern="[A-Za-z]{3,}">
```

==========================
## autocomplete-pattern
==========================
HTML - Формы - Автозаполнение
--------------------------------------------
`autocomplete` указывает браузеру подсказки, `inputmode` — тип раскладки на мобильных.
```html
<input type="email" autocomplete="email">
<input type="text" inputmode="numeric" pattern="[0-9]*">
```

==========================
## semantic-layout
==========================
HTML - Семантика - Области страницы
--------------------------------------------
Семантические блоки страницы для логичной структуры и доступности.
```html
<header>Шапка</header>
<nav>Навигация</nav>
<main>Контент</main>
<footer>Подвал</footer>
```

==========================
## main-section-article
==========================
HTML - Семантика - Основной контент
--------------------------------------------
`main` — главный контент. `section` — смысловой раздел. `article` — самостоятельный материал (пост/новость).
```html
<main>
  <section>
    <article>
      <h2>Новость</h2>
    </article>
  </section>
</main>
```

==========================
## aside
==========================
HTML - Семантика - Боковая панель
--------------------------------------------
Побочный контент (сайдбар, промо-блок, полезные ссылки).
```html
<aside>Сайдбар</aside>
```

==========================
## header-footer
==========================
HTML - Семантика - Верх/низ
--------------------------------------------
`header` — вводная часть (логотип, заголовок). `footer` — подвал (копирайт, ссылки).
```html
<header>Лого + меню</header>
<footer>&copy; 2025</footer>
```

==========================
## nav-breadcrumbs
==========================
HTML - Семантика - Навигация
--------------------------------------------
Основная навигация. Для хлебных крошек добавляйте `aria-label="breadcrumb"` и список.
```html
<nav aria-label="breadcrumb">
  <ol>
    <li><a href="/">Home</a></li>
    <li>Статья</li>
  </ol>
</nav>
```

==========================
## time-address
==========================
HTML - Семантика - Дата/контакты
--------------------------------------------
`time` — машиночитаемая дата. `address` — контакты автора/организации.
```html
<time datetime="2025-08-11">11.08.2025</time>
<address>info@example.com</address>
```

==========================
## details-summary
==========================
HTML - Семантика - Раскрывающиеся блоки
--------------------------------------------
`details`/`summary` — спойлер/аккордеон.
```html
<details>
  <summary>Подробнее</summary>
  Скрытый текст
</details>
```

==========================
## dialog
==========================
HTML - Семантика - Диалог
--------------------------------------------
Нативное модальное окно. Методы: `show()`, `showModal()`, `close()`.
```html
<dialog id="dlg"><p>Привет!</p><form method="dialog"><button>OK</button></form></dialog>
```
```js
document.getElementById('dlg').showModal();
```

==========================
## iframe
==========================
HTML - Встраивание - Фреймы
--------------------------------------------
Встраивание страниц. Безопасность: `sandbox`, `allow`, `referrerpolicy`.
```html
<iframe src="https://example.com" width="600" height="400" loading="lazy" sandbox></iframe>
```

==========================
## embed-object-param
==========================
HTML - Встраивание - Объекты
--------------------------------------------
`embed` — внешний контент (PDF, плеер). `object`/`param` — реже используются.
```html
<embed src="/docs/file.pdf" type="application/pdf" width="600" height="400">
```

==========================
## canvas
==========================
HTML - Встраивание - Графика JS
--------------------------------------------
Полотно для рисования через Canvas API/WebGL.
```html
<canvas id="cv" width="300" height="150"></canvas>
```
```js
const ctx = cv.getContext('2d'); ctx.fillRect(10,10,100,50);
```

==========================
## svg
==========================
HTML - Встраивание - Векторная графика
--------------------------------------------
Векторная графика прямо в разметке; легко стилизуется CSS.
```html
<svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10"/></svg>
```

==========================
## template-slot
==========================
HTML - Служебные - Шаблоны
--------------------------------------------
`template` хранит невидимый контент для клонирования через JS. `slot` — в Web Components.
```html
<template id="rowTmpl"><tr><td class="name"></td><td class="price"></td></tr></template>
```

==========================
## noscript
==========================
HTML - Служебные - JS отключён
--------------------------------------------
Контент, показываемый, если у пользователя отключён JavaScript.
```html
<noscript>Для работы сайта требуется JavaScript.</noscript>
```

==========================
## meta-viewport-favicons
==========================
HTML - Метаданные - Вьюпорт и иконки
--------------------------------------------
Вьюпорт для адаптивности, favicon и иконки приложений.
```html
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="/favicon.ico">
<link rel="apple-touch-icon" href="/icons/icon-180.png">
```

==========================
## opengraph-twitter
==========================
HTML - Метаданные - Соцсети
--------------------------------------------
Open Graph/Twitter Cards — как страница выглядит в предпросмотрах соцсетей.
```html
<meta property="og:title" content="Заголовок">
<meta property="og:description" content="Описание">
<meta property="og:image" content="https://example.com/og.jpg">
<meta property="og:url" content="https://example.com/page">
<meta name="twitter:card" content="summary_large_image">
```

==========================
## preload-prefetch
==========================
HTML - Производительность - Предзагрузка
--------------------------------------------
`preload` — критичные ресурсы, `prefetch` — вероятные будущие, `preconnect` — раннее соединение.
```html
<link rel="preload" href="/fonts/inter.woff2" as="font" type="font/woff2" crossorigin>
<link rel="prefetch" href="/next/page.html" as="document">
<link rel="preconnect" href="https://cdn.example.com" crossorigin>
```

==========================
## defer-async-module
==========================
HTML - Производительность - Скрипты
--------------------------------------------
`defer` сохраняет порядок и ждёт парсинг, `async` — максимум скорости (порядок не гарантирован), `type=module` — ES-модули.
```html
<script src="/js/vendor.js" defer></script>
<script src="/js/ads.js" async></script>
<script type="module" src="/js/app.mjs"></script>
```

==========================
## loading-fetchpriority
==========================
HTML - Производительность - Изображения
--------------------------------------------
`loading=lazy/eager` управляет отложенной загрузкой, `fetchpriority` подсказывает важность.
```html
<img src="hero.jpg" alt="Герой" loading="eager" fetchpriority="high">
<img src="gallery1.jpg" alt="Галерея" loading="lazy" fetchpriority="low">
```

==========================
## aria-overview
==========================
HTML - Доступность - ARIA
--------------------------------------------
Используйте нативные теги сначала. ARIA-атрибуты добавляют роли и состояния, когда нативных нет.
```html
<div role="button" aria-pressed="false" tabindex="0">Псевдо-кнопка</div>
```

==========================
## aria-landmarks
==========================
HTML - Доступность - Области
--------------------------------------------
Лендмарки для навигации вспомогательными технологиями.
```html
<header role="banner"></header>
<nav role="navigation"></nav>
<main role="main"></main>
<footer role="contentinfo"></footer>
```

==========================
## aria-controls-live
==========================
HTML - Доступность - Связи и лайв-регионы
--------------------------------------------
`aria-controls` связывает элементы, `aria-live` — динамические области (алерты/уведомления).
```html
<div id="msg" aria-live="polite"></div>
<button aria-controls="msg">Показать</button>
```

==========================
## global-attrs
==========================
HTML - Глобальные атрибуты - Общее
--------------------------------------------
Атрибуты, доступные почти для всех элементов: `id`, `class`, `style`, `title`, `hidden`, `tabindex`, `role`, `data-*`, `aria-*`.
```html
<div id="box" class="card" data-id="42" title="Подсказка" hidden></div>
```

==========================
## performance-best
==========================
HTML - Практики - Производительность
--------------------------------------------
Советы по скорости загрузки.
```md
- Сжимайте и минифицируйте CSS/JS.
- Используйте `preload` для критичных шрифтов/стилей.
- Отложенная загрузка изображений/iframes: `loading="lazy"`.
- Указывайте `width`/`height` у изображений для предотвращения сдвигов (CLS).
- Объединяйте мелкие иконки в SVG-спрайт или иконки шрифтов.
```

==========================
## security-best
==========================
HTML - Практики - Безопасность
--------------------------------------------
Ключевые настройки безопасности на стороне разметки.
```md
- Для ссылок с `target="_blank"` добавляйте `rel="noopener noreferrer"`.
- В iframe используйте `sandbox`, `allow`, `referrerpolicy`.
- Рассмотрите CSP (Content-Security-Policy) через заголовки или `<meta http-equiv>`.
```

==========================
## forms-best
==========================
HTML - Практики - Формы
--------------------------------------------
Удобство, доступность, валидация.
```md
- Используйте `<label>` для всех полей.
- Указывайте `autocomplete` где возможно.
- Для чисел/телефонов используйте `inputmode` и `pattern`.
- Показывайте сообщения об ошибках рядом с полем.
```

==========================
## images-best
==========================
HTML - Практики - Изображения
--------------------------------------------
Качество, мобильность, SEO.
```md
- Обязательно `alt` (кратко и по делу).
- Для адаптива используйте `srcset/sizes` или `picture`.
- Не злоупотребляйте `width=100%` без учёта контейнеров.
- Сжимайте изображения (AVIF/WebP там, где поддерживается).
```