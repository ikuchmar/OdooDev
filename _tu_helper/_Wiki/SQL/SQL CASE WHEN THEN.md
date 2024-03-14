CASE WHEN THEN
==========================

    SELECT 
        CASE
            WHEN Salary < 1000 THEN 'Low'
            WHEN Salary >= 1000 AND Salary < 3000 THEN 'Medium'
            ELSE 'High'
        END AS SalaryCategory,
        COUNT(*) AS EmployeeCount
    FROM
        Employees
    GROUP BY
        CASE
            WHEN Salary < 1000 THEN 'Low'
            WHEN Salary >= 1000 AND Salary < 3000 THEN 'Medium'
            ELSE 'High'
        END;