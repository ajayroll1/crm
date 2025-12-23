#!/usr/bin/env python
"""
Script to check lead status in database
Run: python manage.py shell < check_leads_status.py
Or: python check_leads_status.py (if Django is set up)
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from myapp.models import Lead
from django.db import connection

print("=" * 100)
print("LEAD STATUS CHECK - All Active Leads")
print("=" * 100)
print(f"{'ID':<8} | {'Name':<30} | {'Email':<30} | {'Status':<15} | {'Updated At':<20}")
print("-" * 100)

# Get all active leads
leads = Lead.objects.filter(is_active=True).order_by('-id')[:10]

for lead in leads:
    print(f"{lead.id:<8} | {lead.name[:30]:<30} | {(lead.email or '-')[:30]:<30} | {(lead.conversion_status or 'Pending'):<15} | {str(lead.updated_at)[:19]:<20}")

print("\n" + "=" * 100)
print("SPECIFIC LEADS (Shellie Fischer & SANGMESHWAR KAMLAPURE)")
print("=" * 100)
print(f"{'ID':<8} | {'Name':<40} | {'Status':<15} | {'Assigned To':<15} | {'Updated At':<20}")
print("-" * 100)

# Get specific leads
specific_leads = Lead.objects.filter(
    is_active=True
).filter(
    name__icontains='Shellie'
) | Lead.objects.filter(
    is_active=True
).filter(
    name__icontains='SANGMESHWAR'
)

for lead in specific_leads:
    assigned = lead.assigned_to.get_full_name() if lead.assigned_to else 'Not Assigned'
    print(f"{lead.id:<8} | {lead.name[:40]:<40} | {(lead.conversion_status or 'Pending'):<15} | {assigned[:15]:<15} | {str(lead.updated_at)[:19]:<20}")

print("\n" + "=" * 100)
print("STATUS COUNT SUMMARY")
print("=" * 100)

# Count by status
from django.db.models import Count
status_counts = Lead.objects.filter(is_active=True).values('conversion_status').annotate(count=Count('id')).order_by('-count')

for item in status_counts:
    status = item['conversion_status'] or 'Pending'
    count = item['count']
    print(f"{status:<20} : {count}")

print("=" * 100)

# Direct SQL query
print("\n" + "=" * 100)
print("DIRECT SQL QUERY RESULT")
print("=" * 100)

cursor = connection.cursor()
cursor.execute("""
    SELECT 
        id,
        name,
        conversion_status,
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
        id DESC
""")

rows = cursor.fetchall()
print(f"{'ID':<8} | {'Name':<40} | {'Status':<15} | {'Updated At':<20}")
print("-" * 100)
for row in rows:
    print(f"{row[0]:<8} | {row[1][:40]:<40} | {(row[2] or 'Pending'):<15} | {str(row[3])[:19]:<20}")

print("=" * 100)


