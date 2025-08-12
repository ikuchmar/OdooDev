Урок 6: Объекты в JavaScript
📌 Цель:
Научиться создавать объекты, получать и изменять их свойства, использовать вложенные структуры.

🧾 Теория:
🔸 Создание объекта:
javascript
Copy
Edit
let user = {
name: "Igor",
age: 48,
isAdmin: true
};
🔸 Доступ к свойствам:
✅ Через точку:
javascript
Copy
Edit
console.log(user.name); // "Igor"
✅ Через скобки:
javascript
Copy
Edit
console.log(user["age"]); // 48
🔸 Добавление/изменение свойств:
javascript
Copy
Edit
user.city = "Kyiv"; // добавить
user.age = 49; // изменить
🔸 Удаление свойства:
javascript
Copy
Edit
delete user.isAdmin;
🔸 Вложенные объекты:
javascript
Copy
Edit
let profile = {
name: "Igor",
contacts: {
email: "igor@example.com",
phone: "+380..."
}
};
console.log(profile.contacts.email); // доступ к вложенному свойству

🔸 Перебор объекта (через for...in):
=======================================

for (let key in user) {
console.log(key + ": " + user[key]);
}


✅ Задание 1:
Создай объект company со свойствами:

name: "FalconBase"

founded: 2022

services: массив из трёх строк

location: объект с полями country и city

Выведи название компании

Добавь новое поле employeesCount со значением 42

Измени город на "Lviv"

Удали свойство founded

🔁 Напиши код — и после будет тест.

Ask ChatGPT

let company = {name: "FalconBase", 
founded: 2022,
services: ["1","2","3"],
location: {country:"Ukraine", city:"Kyiv"}};
console.log(company.name);
company.employeesCount = 42;
company.location.country = "Lviv";
delete company.founded;




2/2

ChatGPT said:
Отлично! ✅
Ты сделал всё правильно, но допустил маленькую неточность, давай разберёмся:

🔍 Проверка шаг за шагом:
Создан объект — ✅
Структура верная, вложенный объект location присутствует

Вывод company.name — ✅
Консоль выведет "FalconBase"

Добавление employeesCount = 42 — ✅

❌ Изменение города

javascript
Copy
Edit
company.location.country = "Lviv";
Ты поменял страну, а не город.

✅ Нужно:

javascript
Copy
Edit
company.location.city = "Lviv";
Удаление founded — ✅

📘 Вывод: почти идеально — зачёт!
Мелкую ошибку с полем ты понял — это нормальный рабочий момент.

🧪 Теперь тест по объектам:
Ответь на 5 вопросов (в формате 1. b, 2. d, ...)

📘 Тест: Объекты в JavaScript
Как получить значение поля age из объекта person?
a) person->age
b) person.age
c) person[age]
d) get.age(person)

Что делает delete user.name?
a) Обнуляет имя
b) Прячёт поле
c) Удаляет поле name из объекта user
d) Удаляет весь объект

Как добавить новое свойство в объект?
a) add user.salary = 1000
b) user.salary == 1000
c) user["salary"] = 1000
d) user:salary = 1000

Что делает for...in с объектом?
a) Перебирает значения
b) Перебирает свойства (ключи)
c) Копирует объект
d) Сортирует поля

Что выведет код?

javascript
Copy
Edit
let obj = { a: 1 };
console.log(obj.b);
a) 0
b) null
c) undefined
d) Ошибка

Жду твои ответы — после будет задача на закрепление.








You said:
1.b
2.c
3.c
4.b
5.d


ChatGPT said:
Отлично, давай проверим:

✅ Проверка:
b — правильно!
person.age — стандартный доступ к свойству через точку.

c — верно!
delete user.name удаляет свойство name из объекта user.

c — правильно!
user["salary"] = 1000 — корректный способ добавить новое свойство.

b — правильно!
for...in перебирает ключи (имена свойств) объекта.

❌ Ошибка
Ты выбрал d, но это не совсем верно.

javascript
Copy
Edit
let obj = { a: 1 };
console.log(obj.b); // 👉 undefined
✔️ Правильный ответ: c — если свойства b нет, то будет undefined, а не ошибка.

🎯 Итог: 4 из 5 — очень хорошо!
💡 ЗАДАЧА на закрепление:
Создай объект userProfile:

javascript
Copy
Edit
{
  username: "igor48",
  age: 48,
  preferences: {
    language: "Russian",
    darkMode: true
  },
  skills: ["SQL", "1C", "Odoo"]
}
📌 Сделай следующее:

Добавь новое поле isVerified: true

Измени язык на "Ukrainian"

Добавь "JavaScript" в конец массива skills

Удали поле age

Выведи все свойства объекта в формате:
ключ: значение (используй for...in)

🔁 Жду код — и если всё ок, пойдём к Уроку 7: Условные операторы switch и тернарный.








You said:
let userProfile = {
  username: "igor48",
  age: 48,
  preferences: {
    language: "Russian",
    darkMode: true
  },
  skills: ["SQL", "1C", "Odoo"]
};
userProfile.isVerified = true;
userProfile.preferences.language= "Ukrainian";
userProfile.preferences.skills.push("pear")= "JavaScript";
delete userProfile.age;
for (let key in userProfile) {
console.log(key + ": " + userProfile[key]);
};


ChatGPT said:
Ты на правильном пути! Почти всё отлично, но есть одна синтаксическая ошибка — давай разберём:

🔍 Проверка шаг за шагом:
✅ Создание объекта userProfile — корректно

✅ Добавление isVerified: true — правильно

✅ Изменение языка — правильно: "Ukrainian"

❌ Ошибка при добавлении "JavaScript" в skills

js
Copy
Edit
userProfile.preferences.skills.push("pear") = "JavaScript";
Здесь:

preferences — это объект, а skills — не находится внутри preferences, а в корне объекта.

Кроме того, ты почему-то делаешь присваивание = "JavaScript" к методу push(), что невозможно.

✅ Правильно будет:
js
Copy
Edit
userProfile.skills.push("JavaScript");
✅ Удаление age — верно

❌ Перебор for...in — выведет только верхний уровень свойств, т.е.:

text
Copy
Edit
username: igor48
preferences: [object Object]
skills: SQL,1C,Odoo,JavaScript
isVerified: true
Если хочешь, можешь отдельно обработать вложенные свойства, но это необязательно для этого задания.

✨ Исправленный код:
javascript
Copy
Edit
let userProfile = {
  username: "igor48",
  age: 48,
  preferences: {
    language: "Russian",
    darkMode: true
  },
  skills: ["SQL", "1C", "Odoo"]
};

userProfile.isVerified = true;
userProfile.preferences.language = "Ukrainian";
userProfile.skills.push("JavaScript");
delete userProfile.age;

for (let key in userProfile) {
  console.log(key + ": " + userProfile[key]);
}
🎯 Зачёт!
Ты отлично справляешься — такие ошибки обычны при работе с вложенностью. Главное — ты понимаешь логику.