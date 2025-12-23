-- ============================================
-- SQL Query to Check Status of Both Leads
-- ============================================
-- Copy this query and run it in your SQL database tool
-- (SQLite Browser, MySQL Workbench, pgAdmin, etc.)

-- Query 1: Check both specific leads (Shellie Fischer & SANGMESHWAR KAMLAPURE)
SELECT 
    id AS 'Lead ID',
    name AS 'Name',
    email AS 'Email',
    phone AS 'Phone',
    company AS 'Company',
    conversion_status AS 'Status',
    assigned_to_id AS 'Assigned To ID',
    created_at AS 'Created',
    updated_at AS 'Last Updated'
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

-- Query 2: Simple version - Just ID, Name, and Status
SELECT 
    id,
    name,
    conversion_status AS status
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

-- Query 3: Check all active leads with status
SELECT 
    id,
    name,
    conversion_status AS status,
    updated_at
FROM 
    myapp_lead
WHERE 
    is_active = 1
ORDER BY 
    updated_at DESC
LIMIT 10;


