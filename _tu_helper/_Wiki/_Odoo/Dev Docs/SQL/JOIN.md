INNER JOIN: Возвращает строки, которые имеют совпадающие значения в обеих таблицах.
sql
Копировать код
SELECT 
    Employees.EmployeeID,
    Employees.FirstName,
    Employees.LastName,
    Departments.DepartmentName
FROM
    Employees
INNER JOIN 
    Departments ON Employees.DepartmentID = Departments.DepartmentID;
LEFT JOIN (или LEFT OUTER JOIN): Возвращает все строки из левой таблицы и совпадающие строки из правой таблицы. Если совпадения нет, результат содержит NULL для правой таблицы.
sql
Копировать код
SELECT 
    Employees.EmployeeID,
    Employees.FirstName,
    Employees.LastName,
    Departments.DepartmentName
FROM
    Employees
LEFT JOIN 
    Departments ON Employees.DepartmentID = Departments.DepartmentID;
RIGHT JOIN (или RIGHT OUTER JOIN): Возвращает все строки из правой таблицы и совпадающие строки из левой таблицы. Если совпадения нет, результат содержит NULL для левой таблицы.
sql
Копировать код
SELECT 
    Employees.EmployeeID,
    Employees.FirstName,
    Employees.LastName,
    Departments.DepartmentName
FROM
    Employees
RIGHT JOIN 
    Departments ON Employees.DepartmentID = Departments.DepartmentID;
FULL OUTER JOIN: Возвращает все строки, когда есть совпадение в левой или правой таблице. Если совпадения нет, результат содержит NULL для соответствующей таблицы.
sql
Копировать код
SELECT 
    Employees.EmployeeID,
    Employees.FirstName,
    Employees.LastName,
    Departments.DepartmentName
FROM
    Employees
FULL OUTER JOIN 
    Departments ON Employees.DepartmentID = Departments.DepartmentID;
CROSS JOIN: Возвращает декартово произведение двух таблиц. Каждая строка из первой таблицы соединяется с каждой строкой из второй таблицы.
sql
Копировать код
SELECT 
    Employees.EmployeeID,
    Employees.FirstName,
    Employees.LastName,
    Departments.DepartmentName
FROM
    Employees
CROSS JOIN 
    Departments;