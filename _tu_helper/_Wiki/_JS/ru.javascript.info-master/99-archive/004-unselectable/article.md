archive:
  ref: selection-range

---

# Мышь: отмена выделения, невыделяемые элементы

У кликов мыши есть неприятная особенность.

Двойной клик или нажатие с движением курсора как правило инициируют выделение текста.

Если мы хотим обрабатывать эти события сами, то такое выделение -- некрасиво и неудобно. В этой главе мы рассмотрим основные способы, как делать элемент невыделяемым.

Для полноты картины, среди них будут и такие, которые применимы не только к событиям мыши.

## Способ 1: отмена mousedown/selectstart

Проблема: браузер выделяет текст при движении мышью с зажатой левой кнопкой , а также при двойном клике на элемент. Даже там, где это не нужно.

Если сделать двойной клик на таком элементе, то обработчик сработает. Но побочным эффектом является *выделение текста браузером*.

```html autorun height=60
<span ondblclick="alert('двойной клик!')">Текст</span>
```

Чтобы избежать выделения, мы должны предотвратить действие браузера по умолчанию для события [selectstart](https://developer.mozilla.org/en-US/docs/Web/API/Document/selectstart_event) в IE и `mousedown` в других браузерах.

Полный код элемента, который обрабатывает двойной клик без выделения:

```html autorun height=60
<div ondblclick="alert('Тест')" *!*onselectstart="return false" onmousedown="return false"*/!*>
  Двойной клик сюда выведет "Тест", без выделения
</div>
```

При установке на родителя -- все его потомки станут невыделяемыми:

```html autorun height=140
Элементы списка не выделяются при клике:
<ul onmousedown="return false" onselectstart="return false">
  <li>Винни-Пух</li>
  <li>Ослик Иа</li>
  <li>Мудрая Сова</li>
  <li>Кролик. Просто кролик.</li>
</ul>
```

```smart header="Выделение, всё же, возможно"
Отмена действия браузера при `mousedown/selectstart` отменяет выделение при клике, но не запрещает его полностью.

Если пользователь всё же хочет выделить текстовое содержимое элемента, то он может сделать это.

Достаточно начать выделение (зажать кнопку мыши) не на самом элементе, а рядом с ним. Ведь там отмены не произойдёт, выделение начнётся, и дальше можно передвинуть мышь уже на элемент.
```

## Способ 2: снятие выделения постфактум

Вместо *предотвращения* выделения, можно его снять в обработчике события, *после* того, как оно уже произошло.

Для этого мы используем методы работы с выделением, которые описаны в отдельной главе <info:range-textrange-selection>. Здесь нам понадобится всего лишь одна функция `clearSelection`, которая будет снимать выделение.

Пример со снятием выделения при двойном клике на элемент списка:

```html autorun height=60
<ul>
  <li ondblclick="clearSelection()">Выделение отменяется при двойном клике.</li>
</ul>

<script>
  function clearSelection() {
    if (window.getSelection) {
      window.getSelection().removeAllRanges();
    } else { // старый IE
      document.selection.empty();
    }
  }
</script>
```

У этого подхода есть две особенности, на которые стоит обратить внимание:

- Выделение всё же производится, но тут же снимается. Это выглядит как мигание и не очень красиво.
- Выделение при помощи передвижения зажатой мыши всё ещё работает, так что посетитель имеет возможность выделить содержимое элемента.

## Способ 3: свойство user-select

Существует нестандартное CSS-свойство `user-select`, которое делает элемент невыделяемым.

Оно когда-то планировалось в стандарте CSS3, потом от него отказались, но поддержка в браузерах уже была сделана и потому осталась.

Это свойство работает (с префиксом) везде, кроме IE9-:

```html autorun height=auto
<style>
  b {
    -webkit-user-select: none;
    /* user-select -- это нестандартное свойство */

    -moz-user-select: none;
    /* поэтому нужны префиксы */

    -ms-user-select: none;
  }
</style>

Строка до..
<div ondblclick="alert('Тест')">
  <b>Этот текст нельзя выделить (кроме IE9-)</b>
</div>
.. Строка после
```

Читайте на эту тему также [Controlling Selection with CSS user-select](http://blogs.msdn.com/b/ie/archive/2012/01/11/controlling-selection-with-css-user-select.aspx).

### IE9-: атрибут unselectable="on"

В IE9- нет `user-select`, но есть атрибут [unselectable](http://msdn.microsoft.com/en-us/library/ms534706%28v=vs.85%29.aspx).

Он отменяет выделение, но у него есть особенности:

1. Во-первых, невыделяемость не наследуется. То есть, невыделяемость родителя не делает невыделяемыми детей.
2. Во-вторых, текст, в отличие от `user-select`, всё равно можно выделить, если начать выделение не на самом элементе, а рядом с ним.

```html
<div ondblclick="alert('Тест')" *!*unselectable="on"*/!* style="border:1px solid black">
  Этот текст невыделяем в IE, <em>кроме дочерних элементов</em>
</div>
```

Левая часть текста в IE не выделяется при двойном клике. Правую часть (`em`) можно выделить, т.к. на ней нет атрибута `unselectable`.

```online
В действии:
<div ondblclick="alert('Тест')" unselectable="on" style="border:1px solid black">
  Этот текст невыделяем в IE, <em>кроме дочерних элементов</em>
</div>
```

## Итого

Для отмены выделения есть несколько способов:

1. CSS-свойство `user-select` -- везде кроме IE9- (нужен префикс, нестандарт).
2. Атрибут `unselectable="on"` -- работает для любых IE (должен быть у всех потомков)
3. Отмена действий на `mousedown` и `selectstart`:

    ```js
    elem.onmousedown = elem.onselectstart = function() {
      return false;
    };
    ```
4. Отмена выделения пост-фактум через функцию `clearSelection()`, описанную выше.

Какой же способ выбирать?

Это зависит от задач и вашего удобства, а также конкретного случая. Все описанные способы работают.

Недостаток `user-select` -- в том, что посетитель теряет возможность скопировать текст. А что, если он захочет именно это сделать?

В любом случае эти способы не предназначены для защиты от выделения-и-копирования.

Если уж хочется запретить копирование -- можно использовать событие `oncopy`:

```html autorun height=80 no-beautify
<div oncopy="alert('Копирование запрещено');return false">
  Уважаемый копирователь,
  почему-то автор хочет заставить вас покопаться в исходном коде этой страницы.
  Если вы знаете JS или HTML, то скопировать текст не составит для вас проблемы,
  ну а если нет, то увы...
</div>
```

