
Установка библиотеки:
Copy code
pip install psycopg2

Подключение к базе данных:
python
Copy code
import psycopg2

conn = psycopg2.connect(
    dbname="mydatabase",
    user="myusername",
    password="mypassword",
    host="localhost",
    port="5432"
)
Создание таблицы:
python
Copy code
import psycopg2

conn = psycopg2.connect(
    dbname="mydatabase",
    user="myusername",
    password="mypassword",
    host="localhost",
    port="5432"
)

cur = conn.cursor()
cur.execute("""
    CREATE TABLE employees (
        id serial PRIMARY KEY,
        name varchar(255),
        salary decimal
    );
""")
conn.commit()
Вставка данных в таблицу:
python
Copy code
import psycopg2

conn = psycopg2.connect(
    dbname="mydatabase",
    user="myusername",
    password="mypassword",
    host="localhost",
    port="5432"
)

cur = conn.cursor()
cur.execute("INSERT INTO employees (name, salary) VALUES (%s, %s)", ("John Doe", 50000))
conn.commit()
Получение данных из таблицы:
python
Copy code
import psycopg2

conn = psycopg2.connect(
    dbname="mydatabase",
    user="myusername",
    password="mypassword",
    host="localhost",
    port="5432"
)

cur = conn.cursor()
cur.execute("SELECT id, name, salary FROM employees")
rows = cur.fetchall()
for row in rows:
    print(row)
Обновление данных в таблице:
python
Copy code
import psycopg2

conn = psycopg2.connect(
    dbname="mydatabase",
    user="myusername",
    password="mypassword",
    host="localhost",
    port="5432"
)

cur = conn.cursor()
cur.execute("UPDATE employees SET salary = %s WHERE name = %s", (60000, "John Doe"))
conn.commit()
Удаление данных из таблицы:
python
Copy code
import psycopg2

conn = psycopg2.connect(
    dbname="mydatabase",
    user="myusername",
    password="mypassword",
    host="localhost",
    port="5432"
)

cur = conn.cursor()
cur.execute("DELETE FROM employees WHERE name = %s", ("John Doe",))
conn.commit()