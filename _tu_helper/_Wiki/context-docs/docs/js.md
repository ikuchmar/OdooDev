---

## fetch
==========================
JavaScript - Сеть - HTTP
--------------------------------------------
Функция `fetch` отправляет HTTP-запрос и возвращает промис с ответом.

```javascript
async function loadUsers() {
  const res = await fetch("/api/users");
  if (!res.ok) throw new Error(res.statusText);
  const data = await res.json();
  console.log(data);
}
```
## addEventListener
JavaScript - DOM - События
Регистрирует обработчик события у элемента.

```javascript
const btn = document.querySelector("#save");
btn.addEventListener("click", (e) => {
  e.preventDefault();
  console.log("Saved!");
});
```

