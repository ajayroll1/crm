-- SQL Query to check status of all active leads
-- Run this query in your database (SQLite/PostgreSQL/MySQL)

-- Query 1: Check all active leads with their status
SELECT 
    id,
    name,
    email,
    phone,
    company,
    conversion_status,
    assigned_to_id,
    created_at,
    updated_at
FROM 
    myapp_lead
WHERE 
    is_active = 1
ORDER BY 
    id DESC
LIMIT 20;

-- Query 2: Check specific leads by name (the two leads visible in employee page)
SELECT 
    id,
    name,
    email,
    phone,
    company,
    conversion_status AS status,
    assigned_to_id,
    created_at,
    updated_at
FROM 
    myapp_lead
WHERE 
    is_active = 1
    AND (
        name LIKE '%Shellie Fischer%' 
        OR name LIKE '%SANGMESHWAR KAMLAPURE%'
    )
ORDER BY 
    id DESC;

-- Query 3: Count leads by status
SELECT 
    conversion_status AS status,
    COUNT(*) AS count
FROM 
    myapp_lead
WHERE 
    is_active = 1
GROUP BY 
    conversion_status
ORDER BY 
    count DESC;

-- Query 4: Check recent status updates (last 10)
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


