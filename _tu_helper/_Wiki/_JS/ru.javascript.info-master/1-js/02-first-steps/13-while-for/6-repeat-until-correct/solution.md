
```js run demo
let num;

do {
  num = prompt("Введите число больше 100?", 0);
} while (num <= 100 && num);
```

Цикл `do..while` повторяется, пока верны две проверки:

1. Проверка `num <= 100` -- то есть, введённое число всё ещё меньше `100`.
2. Проверка `&& num` вычисляется в `false`, когда `num` имеет значение `null` или пустая строка `''`. В этом случае цикл `while` тоже нужно прекратить.

Кстати, сравнение `num <= 100` при вводе `null` даст `true`, так что вторая проверка необходима.
