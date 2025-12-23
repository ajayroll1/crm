-- Simple SQL Query to check status of both leads
-- Copy and paste this in your SQL database tool

SELECT 
    id,
    name,
    conversion_status AS status,
    updated_at
FROM 
    myapp_lead
WHERE 
    is_active = 1
    AND (
        name LIKE '%Shellie%' 
        OR name LIKE '%SANGMESHWAR%'
    )
ORDER BY 
    id DESC;


