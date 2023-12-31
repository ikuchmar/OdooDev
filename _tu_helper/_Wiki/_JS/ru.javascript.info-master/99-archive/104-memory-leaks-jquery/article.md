archive:
  ref: null

---


# Утечки памяти при использовании jQuery

В jQuery для хранения обработчиков событий и других вспомогательных данных, связанных с DOM-элементами, используется внутренний объект, который в jQuery 1 доступен через [$.data](https://api.jquery.com/jQuery.data/).

В jQuery 2 доступ к нему закрыт через замыкание, он стал локальной переменной внутри jQuery с именем `data_priv`, но в остальном всё работает точно так, как описано, и с теми же последствиями.

## $.data

Встроенная функция `$.data` позволяет хранить и привязывать произвольные значения к DOM-узлам.

Например:

```js no-beautify
// присвоить
$(document).data('prop', { anything: "любой объект" })

// прочитать
alert( $(document).data('prop').anything ) // любой объект
```

Реализована она хитрым образом. Данные не хранятся в самом элементе, а во внутреннем объекте jQuery.

jQuery-вызов `elem.data(prop, val)` делает следующее:

1. Элемент получает уникальный идентификатор, если у него такого ещё нет:

    ```js
    elem[jQuery.expando] = id = ++jQuery.uuid; // средствами jQuery
    ```

  `jQuery.expando` -- это случайная строка, сгенерированная jQuery один раз при входе на страницу. Уникальное свойство, чтобы ничего важного не перезаписать.
  
2. ...А сами данные сохраняются в специальном объекте `jQuery.cache`:

    ```js no-beautify
    jQuery.cache[id]['prop'] = { anything: "любой объект" };
    ```

Когда данные считываются из элемента:

1. Уникальный идентификатор элемента извлекается из `id = elem[ jQuery.expando]`.
2. Данные считываются из `jQuery.cache[id]`.

Смысл этого API в том, что DOM-элемент никогда не ссылается на JavaScript объект напрямую. Задействуется идентификатор, а сами данные хранятся в `jQuery.cache`. Утечек в IE не будет.

К тому же все данные известны библиотеке, так что можно клонировать с ними и т.п.

Как побочный эффект -- возникает утечка памяти, если элемент удалён из DOM без дополнительной очистки.

## Примеры утечек в jQuery

Следующая функция `leak` создаёт jQuery-утечку во всех браузерах:

```html run
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/2.1.3/jquery.min.js"></script>

<div id="data"></div>

<script>
  function leak() {

*!*
    $('<div/>')
      .html(new Array(1000).join('text'))
      .click(function() {})
      .appendTo('#data');

    document.getElementById('data').innerHTML = ''; // (*)
*/!*

  }

  var interval = setInterval(leak, 10)
</script>

Утечка идёт...

<input type="button" onclick="clearInterval(interval)" value="stop" />
```

Утечка происходит потому, что обработчик события в jQuery хранится в данных элемента. В строке `(*)` элемент удалён очисткой родительского `innerHTML`, но в `jQuery.cache` данные остались.

Более того, система обработки событий в jQuery устроена так, что вместе с обработчиком в данных хранится и ссылка на элемент, так что в итоге оба -- и обработчик и элемент -- остаются в памяти вместе со всем замыканием!

Ещё более простой пример утечки:

Этот код также создаёт утечку:

```js
function leak() {
  $('<div/>')
    .click(function() {})
}
```

...То есть, мы создаём элемент, вешаем на него обработчик... И всё.

Такой код ведёт к утечке памяти как раз потому, что элемент `<div>` создан, но нигде не размещён :). После выполнения функции ссылка на него теряется. Но обработчик события `click` уже сохранил данные в `jQuery.cache`, которые застревают там навсегда.

## Используем jQuery без утечек

Чтобы избежать утечек, описанных выше, для удаления элементов используйте функции jQuery API, а не чистый JavaScript.

Методы <a href="https://api.jquery.com/remove/">remove()</a>, <a href="https://api.jquery.com/empty">empty()</a> и <a href="https://api.jquery.com/html">html()</a> проверяют дочерние элементы на наличие данных и очищают их. Это несколько замедляет процедуру удаления, но зато освобождается память.

К счастью обнаружить такие утечки легко. Проверьте размер `$.cache`. Если  он большой и растёт, то изучите кэш, посмотрите, какие записи остаются и почему.

## Улучшение производительности jQuery

У способа организации внутренних данных, применённого в jQuery, есть важный побочный эффект.

Функции, удаляющие элементы, также должны удалить и связанные с ними внутренние данные. Для этого нужно для каждого удаляемого элемента проверить -- а нет ли чего во внутреннем хранилище? И, если есть -- удалить.

Представим, что у нас есть большая таблица `<table>`, и мы хотим обновить её содержимое на новое. Вызов `$('table').html(новые данные)` перед вставкой новых данных аккуратно удалит старые: пробежит по всем ячейкам и проверит внутреннее хранилище.

Если это большая таблица, то обработчики, скорее всего, стоят не на ячейках, а на самом элементе `<table>`, то есть используется делегирование. А, значит, тратить время на проверку всех подэлементов ни к чему.

Но jQuery-то об этом не знает!

Чтобы "грязно" удалить элемент, без чистки, мы можем сделать это через "обычные" DOM-вызовы или воспользоваться методом <a href="https://api.jquery.com/detach">detach()</a>. Его официальное назначение -- в том, чтобы убрать элемент из DOM, но сохранить возможность для вставки (и, соответственно, оставить на нём все данные). А неофициальное -- быстро убрать элемент из DOM, без чистки.

Возможен и промежуточный вариант: никто не мешает сделать  `elem.detach()` и поместить вызов `elem.remove()` в `setTimeout`. В результате очистка будет происходить асинхронно и незаметно.

## Итого

- Утечки памяти при использовании jQuery возможны, если через DOM-методы удалять элементы, к которым привязаны данные или обработчики.
- Чтобы утечки не было, достаточно убедиться, что элемент удаляется при помощи методов jQuery.
- Побочный эффект -- при удалении элементов jQuery должна проверить наличие данных для них. Это сильно замедляет процесс удаления большого поддерева DOM.
- Если мы знаем, что обработчиков и данных нет -- гораздо быстрее удалять элементы при помощи вызова `detach` или обычного DOM.

