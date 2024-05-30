UNION: Объединяет результаты двух SELECT-запросов в один набор результатов. 
Каждый SELECT-запрос должен возвращать одно и то же количество столбцов с совместимыми типами данных.

    SELECT 
        EmployeeID,
        FirstName,
        LastName
    FROM 
        Employees
    UNION
    SELECT 
        CustomerID AS ID,
        FirstName,
        LastName
    FROM 
        Customers;