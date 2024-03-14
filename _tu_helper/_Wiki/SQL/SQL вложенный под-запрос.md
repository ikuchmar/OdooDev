WHERE
==========================

    SELECT 
        ProductID,
        ProductName,
        UnitPrice
    FROM
        Products
    WHERE
        UnitPrice > (SELECT AVG(UnitPrice) FROM Products);

SELECT
============================

    SELECT 
        OrderID,
        (SELECT COUNT(*) FROM OrderDetails WHERE OrderID = Orders.OrderID) AS NumberOfItems
    FROM
        Orders;

FROM
============================

    SELECT 
        CustomerID,
        TotalSales
    FROM
        (SELECT 
             CustomerID,
             SUM(TotalAmount) AS TotalSales
         FROM
             Orders
         GROUP BY
             CustomerID) AS CustomerSales
    WHERE
        TotalSales > 1000;
