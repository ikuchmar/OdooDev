Для генерации QWeb шаблона на основе списка словарей, можно использовать модуль jinja2, который входит в состав фреймворка Flask.

Пример скрипта на Python для генерации QWeb шаблона по списку словарей:

import jinja2

# Описание шаблона в виде списка словарей
template_data = [
    {'name': 'John', 'age': 25, 'email': 'john@example.com'},
    {'name': 'Alice', 'age': 30, 'email': 'alice@example.com'},
    {'name': 'Bob', 'age': 35, 'email': 'bob@example.com'}
]

# Описание QWeb шаблона в виде строки
qweb_template = '''
    <t t-name="contact_list">
        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Age</th>
                    <th>Email</th>
                </tr>
            </thead>
            <tbody>
                {% for contact in contacts %}
                <tr>
                    <td>{{ contact['name'] }}</td>
                    <td>{{ contact['age'] }}</td>
                    <td>{{ contact['email'] }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </t>
'''

# Создание объекта шаблона Jinja2
jinja_template = jinja2.Template(qweb_template)

# Генерация QWeb шаблона
generated_qweb_template = jinja_template.render(contacts=template_data)

print(generated_qweb_template)
В данном примере создается список словарей template_data, содержащий информацию о контактах.
Затем создается строковое описание QWeb шаблона qweb_template,
в котором используются теги Jinja2 для вставки данных из списка template_data.

С помощью модуля jinja2 создается объект шаблона jinja_template,
а затем вызывается метод render(), который генерирует QWeb шаблон,
используя данные из списка template_data. Результат выводится на экран.