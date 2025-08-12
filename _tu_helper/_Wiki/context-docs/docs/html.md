
---
## html
========================
HTML - Базовые теги
------------------------
Тег `<html>` является корневым элементом HTML-документа. Он содержит все остальные элементы страницы.

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Document</title>
</head>
<body>
    
</body>
</html>
```

---
## head
========================
HTML - Базовые теги - Метаинформация
Тег `<head>` содержит метаинформацию о документе: заголовок, кодировку, стили и скрипты.

```html
<head>
    <meta charset="UTF-8">
    <title>Заголовок страницы</title>
    <link rel="stylesheet" href="styles.css">
</head>
```

## body
HTML - Базовые теги - Структура
Тег `<body>` представляет основное содержимое HTML-документа, видимое пользователю на странице.

```html
<body>
    <h1>Заголовок</h1>
    <p>Текст страницы</p>
</body>
```

## img
HTML - Базовые теги - Изображения
Тег `<img>` используется для отображения изображений. Он должен содержать атрибут `src`.

```html
<img src="image.jpg" alt="Описание изображения">
```

## a
HTML - Базовые теги - Ссылки
Тег `<a>` используется для создания гиперссылок.

```html
<a href="https://example.com">Перейти на сайт</a>
```

## form
HTML - Формы - Базовое
Тег `<form>` используется для создания формы, которая может отправлять данные на сервер.

```html
<form action="/submit" method="post">
    <input type="text" name="username" placeholder="Имя">
    <button type="submit">Отправить</button>
</form>
```

## input
HTML - Формы - Поля ввода
Тег `<input>` представляет поле ввода данных.

```html
<input type="text" name="username" placeholder="Введите имя">
```