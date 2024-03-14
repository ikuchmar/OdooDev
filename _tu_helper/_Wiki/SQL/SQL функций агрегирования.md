SUM():
===========================
    SELECT 
        CustomerID,
        SUM(TotalAmount) AS TotalSales
    FROM
        Sales
    GROUP BY
        CustomerID;

AVG() для вычисления среднего 
================================
    SELECT 
        Department,
        AVG(Age) AS AverageAge
    FROM
        Employees
    GROUP BY
        Department;

MAX() для нахождения максимума
==============================

    SELECT 
        Department,
        MAX(Salary) AS MaxSalary
    FROM
        Employees
    GROUP BY
        Department;

COUNT() для подсчета количества 
====================================
    SELECT 
        ProductID,
        COUNT(*) AS OrderCount
    FROM
        Orders
    GROUP BY
        ProductID;

COUNT() используется для подсчета количества уникальных значений столбца CustomerID, и оператор DISTINCT обеспечивает учет только уникальных значений.
=======================================

    SELECT 
        COUNT(DISTINCT CustomerID) AS UniqueCustomersCount
    FROM
        Orders;