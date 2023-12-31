archive:
  ref: null

---

# Введение

На протяжении долгого времени в программировании применялся [процедурный подход](https://ru.wikipedia.org/wiki/%D0%9F%D1%80%D0%BE%D1%86%D0%B5%D0%B4%D1%83%D1%80%D0%BD%D0%BE%D0%B5_%D0%BF%D1%80%D0%BE%D0%B3%D1%80%D0%B0%D0%BC%D0%BC%D0%B8%D1%80%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D0%B5). При этом программа состоит из функций, вызывающих друг друга.

Гораздо позже появилось [объектно-ориентированное программирование](https://ru.wikipedia.org/wiki/%D0%9E%D0%B1%D1%8A%D0%B5%D0%BA%D1%82%D0%BD%D0%BE-%D0%BE%D1%80%D0%B8%D0%B5%D0%BD%D1%82%D0%B8%D1%80%D0%BE%D0%B2%D0%B0%D0%BD%D0%BD%D0%BE%D0%B5_%D0%BF%D1%80%D0%BE%D0%B3%D1%80%D0%B0%D0%BC%D0%BC%D0%B8%D1%80%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D0%B5) (ООП), которое позволяет группировать функции и данные в единой сущности -- "объекте".

При объектно-ориентированной разработке мы описываем происходящее на уровне объектов, которые создаются, меняют свои свойства, взаимодействуют друг с другом и (в случае браузера) со страницей, в общем, живут.

Например, "пользователь", "меню", "компонент интерфейса"... При объектно-ориентированном подходе каждый  объект должен представлять собой интуитивно понятную сущность, у которой есть методы и данные.

```warn header="ООП -- это не просто объекты"
В JavaScript объекты часто используются просто как коллекции.

Например, встроенный объект [Math](https://developer.mozilla.org/en/JavaScript/Reference/Global_Objects/Math) содержит функции (`Math.sin`, `Math.pow`, ...) и данные (константа `Math.PI`).

При таком использовании объектов мы не можем сказать, что "применён объектно-ориентированный подход". В частности, никакую "единую сущность" `Math` из себя не представляет, это просто коллекция независимых функций с общим префиксом `Math`.
```

Мы уже работали в ООП-стиле, создавая объекты такого вида:

```js run
function User(name) {

  this.sayHi = function() {
    alert( "Привет, я " + name );
  };

}

var vasya = new User("Вася"); // создали пользователя
vasya.sayHi(); // пользователь умеет говорить "Привет"
```

Здесь мы видим ярко выраженную сущность -- `User` (посетитель). Используя терминологию ООП, такие конструкторы часто называют *классами*, то есть можно сказать "класс `User`".

```smart header="Класс в ООП"
[Классом](https://en.wikipedia.org/wiki/Class_(computer_programming)) в объектно-ориентированной разработке называют шаблон/программный код, предназначенный для создания объектов и методов.

В JavaScript классы можно организовать по-разному. Говорят, что класс `User` написан в "функциональном" стиле. Далее мы также увидим "прототипный" стиль.
```

ООП -- это наука о том, как делать правильную архитектуру. У неё есть свои принципы, например [SOLID](https://ru.wikipedia.org/wiki/SOLID_%28%D0%BE%D0%B1%D1%8A%D0%B5%D0%BA%D1%82%D0%BD%D0%BE-%D0%BE%D1%80%D0%B8%D0%B5%D0%BD%D1%82%D0%B8%D1%80%D0%BE%D0%B2%D0%B0%D0%BD%D0%BD%D0%BE%D0%B5_%D0%BF%D1%80%D0%BE%D0%B3%D1%80%D0%B0%D0%BC%D0%BC%D0%B8%D1%80%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D0%B5%29).

По приёмам объектно-ориентированной разработки пишут книги, к примеру:

- <a href="https://www.ozon.ru/context/detail/id/3905587/?partner=iliakan">Объектно-ориентированный анализ и проектирование с примерами приложений.</a>
<i>Гради Буч и др.</i>.
- <a href="https://www.ozon.ru/context/detail/id/2457392/?partner=iliakan">Приёмы объектно-ориентированного проектирования. Паттерны проектирования.</a>
<i>Э. Гамма, Р. Хелм, Р. Джонсон, Дж. Влиссидес.</i>

Здесь мы не имеем возможности углубиться в теорию ООП, поэтому чтение таких книг рекомендуется. Хотя основные принципы, как использовать ООП правильно, мы, всё же, затронем.