optional="show" "hide"   Опціональне відображення полів
===================================================

    <tree>
       <field name="name" optional="show"/>
       <field name="name1" optional="hide"/>
       <field name="state" optional="show"/>
    </tree>

Прописаний для поля атрибут optional надає користувачу можливість відображати або приховувати поле у списку. Змінювати режим відображення користувач може лише полям з даним атрибутом. Якщо хоча б одне поле має цей атрибут, у списку з'явиться віджет у вигляді 3х крабочек, який розкриє меню для вибору стану відображення поля. Значення атрибуту буде поведінкою поля за замовчуванням (потім буде братись визначене користувачем). Значення show буде відображати поле, а hide відповідно приховувати.
Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Представлення списком6.png