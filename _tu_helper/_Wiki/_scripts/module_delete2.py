import psycopg2

conn = psycopg2.connect(
    host="your_host",
    database="your_database",
    user="your_username",
    password="your_password"
)

cur = conn.cursor()

cur.execute("SELECT * FROM ir_module_module WHERE name = 'module_name';")

rows = cur.fetchall()

for row in rows:
    print(row)

cur.close


def delete_module(module_name):
    # устанавливаем соединение с базой данных
    conn = psycopg2.connect(database="my_database", user="my_user", password="my_password", host="my_host",
                            port="my_port")
    cursor = conn.cursor()

    # выполняем запрос на удаление строк из таблицы "ir.module.module"
    cursor.execute(f"DELETE FROM ir_module_module WHERE name = '{module_name}'")
    conn.commit()

    # закрываем соединение
    cursor.close()
    conn.close()

    print(f"Модуль {module_name} успешно удален")

module_name = 'my_module'
delete_module(module_name)
