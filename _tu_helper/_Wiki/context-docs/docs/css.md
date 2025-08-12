==========================
## selectors
==========================
CSS - Основы - Селекторы
--------------------------------------------
Селекторы определяют, к каким элементам применять стили.

```css
/* По тегу */
p { margin: 0; }
/* По классу */
.card { padding: 1rem; }
/* По id */
#main { max-width: 960px; }
/* Атрибутный */
input[type="text"] { border: 1px solid #ccc; }
```
## flex
CSS - Макеты - Flexbox
Flexbox упрощает построение одномерных макетов.

```css
.container {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
}
.container > .item { flex: 1; }
```
