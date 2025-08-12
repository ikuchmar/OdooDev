Урок 7: Оператор switch и тернарный оператор ?
📌 Цель:
Научиться использовать альтернативы if...else — для удобного выбора вариантов.

🧾 Теория:
🔸 switch — выбор из множества случаев:
javascript
Copy
Edit
let fruit = "banana";

switch (fruit) {
  case "apple":
    console.log("Это яблоко");
    break;
  case "banana":
    console.log("Это банан");
    break;
  default:
    console.log("Неизвестный фрукт");
}
💡 Обязательно:
break — завершает выполнение блока.

default — сработает, если ни один case не подошёл.

🔸 Тернарный оператор ? :
javascript
Copy
Edit
let age = 20;
let status = age >= 18 ? "взрослый" : "несовершеннолетний";
console.log(status);
📌 Структура:
javascript
Copy
Edit
условие ? значение_если_true : значение_если_false
✅ Задание 1:
Объяви переменную day = "Tuesday"

С помощью switch выведи в консоль:

"Начало недели" — для "Monday"

"Середина недели" — для "Tuesday" и "Wednesday"

"Конец недели" — для "Thursday" и "Friday"

"Выходной" — для "Saturday" и "Sunday"

🔁 Напиши код — после этого будет тест и задача.








You said:
let day = "Tuesday";

switch (day) { 
  case "Monday":
    console.log("Начало недели");
    break;
  case "Tuesday" or "Wednesday": 
    console.log("Середина недели");
    break;
  case "Thursday" or "Friday": 
    console.log("Конец недели");
    break;
  case "Saturday" or "Sunday": 
    console.log("Выходной");
    break;
  default: 
    console.log("Неизвестный фрукт");
}


ChatGPT said:
Ты правильно уловил суть switch, но в JavaScript нельзя использовать or в case — это не работает.
Нужно на каждый вариант писать отдельный case, даже если действия одинаковы.

❌ Проблема:
javascript
Copy
Edit
case "Tuesday" or "Wednesday":
⛔ JavaScript этого не поймёт.

✅ Правильный вариант:
javascript
Copy
Edit
let day = "Tuesday";

switch (day) {
  case "Monday":
    console.log("Начало недели");
    break;
  case "Tuesday":
  case "Wednesday":
    console.log("Середина недели");
    break;
  case "Thursday":
  case "Friday":
    console.log("Конец недели");
    break;
  case "Saturday":
  case "Sunday":
    console.log("Выходной");
    break;
  default:
    console.log("Неизвестный день");
}
✅ Остальные части твоего кода — отличные (структура, break, console.log).

🧪 Тест по switch и тернарному оператору:
Ответь на 5 вопросов (в формате 1. b, 2. a...)

📘 Тест
Что делает break в switch?
a) Завершает весь скрипт
b) Переходит к следующему case
c) Завершает выполнение switch
d) Завершает программу

Что выведет?

javascript
Copy
Edit
let x = 10;
let result = x > 5 ? "yes" : "no";
console.log(result);
a) no
b) undefined
c) yes
d) Ошибка

Что делает тернарный оператор ??
a) Делает копию переменной
b) Проверяет тип
c) Упрощает if-else
d) Запускает цикл

Что выведет код?

javascript
Copy
Edit
let fruit = "pear";

switch (fruit) {
  case "apple":
    console.log("Яблоко");
    break;
  default:
    console.log("Неизвестный фрукт");
}
a) pear
b) Яблоко
c) Неизвестный фрукт
d) Ошибка

Что будет, если в switch забыть break?
a) Будет ошибка
b) Ничего не выведется
c) Выполнятся все последующие case до break
d) Будет бесконечный цикл

Жду твои ответы — и после дам задачу на закрепление.








You said:
1.c
2.c
3.c
4.c
5.c


ChatGPT said:
Прекрасно! ✅ Давай проверим:

✅ Проверка:
c — верно!
break завершает выполнение текущего switch.

c — правильно!
x > 5 → true → результат: "yes"

c — абсолютно верно!
Тернарный оператор — короткая форма if...else.

c — правильно!
"pear" не попадает ни в один case, срабатывает default.

c — верно!
Если забыть break, выполнятся все последующие case до первого break — это называется "проваливание" (fallthrough).

🎉 Результат: 5 из 5 — ты молодец!

💡 ЗАДАЧА на закрепление:
Объяви переменную score (оценка по 5-балльной шкале, от 1 до 5).
С помощью тернарного оператора определи:

"отлично" — если 5

"хорошо" — если 4

"удовлетворительно" — если 3

"плохо" — если 1 или 2

🧠 Подсказка:
Для 3 условий лучше использовать вложенные тернарные операторы

📌 Пример:

javascript
Copy
Edit
let result = score === 5 ? "отлично" :
             score === 4 ? "хорошо" :
             ...
🔁 Жду твой код — если всё верно, перейдём к Уроку 8: Асинхронность и setTimeout, Promise, async/await (вводно).








You said:
let score = 4;

let result = score === 5 ? "отлично" :
             score === 4 ? "хорошо" :
             score === 3 ? "удовлетворительно" :
             (score === 2 || score === 1) ? "плохо" :
             "неизвестная оценка";

console.log(result);



2/2

ChatGPT said:
Превосходно! ✅
Ты написал вложенные тернарные условия абсолютно корректно:

🔍 Проверка:
score = 4 → срабатывает score === 4 → результат "хорошо"

Все случаи охвачены, даже защита на неправильное значение: "неизвестная оценка" — отличная практика!

Скобки в score === 2 || score === 1 — это 🔥 правильно и аккуратно!

✔️ Вывод:
Задание выполнено на отлично — ты уверенно работаешь с тернарными операторами.