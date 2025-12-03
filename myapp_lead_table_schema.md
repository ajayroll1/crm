# Database Schema: myapp_lead

## Table Information
- **Table Name**: `myapp_lead`
- **Django Model**: `Lead` (in `myapp/models.py`, line 8)
- **App Name**: `myapp`
- **Model Name**: `Lead`

---

## Complete Schema Structure

### Primary Key
| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| `id` | INTEGER (Auto-increment) | PRIMARY KEY, NOT NULL | Auto-generated unique identifier |

---

### Basic Information Fields

| Column Name | Data Type | Max Length | Nullable | Default | Description |
|------------|-----------|------------|----------|---------|-------------|
| `name` | VARCHAR | 100 | NOT NULL | - | Full Name of the lead (Required) |
| `email` | VARCHAR | 254 | NULL | NULL | Email address (Optional, validated) |
| `phone` | VARCHAR | 20 | NULL | NULL | Phone number (Optional, validated: 7-20 digits) |
| `company` | VARCHAR | 100 | NULL | NULL | Company name (Optional) |
| `address` | TEXT | - | NULL | NULL | Address (Optional) |

---

### Lead Management Fields

| Column Name | Data Type | Max Length | Nullable | Default | Description |
|------------|-----------|------------|----------|---------|-------------|
| `source` | VARCHAR | 50 | NOT NULL | - | Lead Source (Choices: Website, Referral, Cold Call, Social, Event, Other) |
| `priority` | VARCHAR | 10 | NOT NULL | 'Med' | Priority Level (Choices: Low, Med, High) |
| `owner` | VARCHAR | 100 | NOT NULL | - | Assigned Owner name (Required) |
| `use_case` | TEXT | - | NOT NULL | - | Use Case description (Required) |

---

### Foreign Key Relationships

| Column Name | Data Type | References | On Delete | Nullable | Description |
|------------|-----------|------------|-----------|----------|-------------|
| `assigned_to_id` | INTEGER | `myapp_employee.id` | SET NULL | NULL | Foreign Key to Employee (who is assigned this lead) |
| `imported_by_id` | INTEGER | `myapp_employee.id` | SET NULL | NULL | Foreign Key to Employee (who imported this lead) |

---

### Next Actions Fields

| Column Name | Data Type | Max Length | Nullable | Default | Description |
|------------|-----------|------------|----------|---------|-------------|
| `next_action` | VARCHAR | 20 | NULL | 'None' | Next Action (Choices: Call, Email, Demo, Meeting, None) |
| `due_date` | DATE | - | NULL | NULL | Due Date for next action |
| `due_time` | TIME | - | NULL | NULL | Due Time for next action |

---

### Optional Information Fields

| Column Name | Data Type | Max Length | Nullable | Default | Description |
|------------|-----------|------------|----------|---------|-------------|
| `website` | VARCHAR | 200 | NULL | NULL | Website URL (Optional, validated as URL) |
| `industry` | VARCHAR | 100 | NULL | NULL | Industry name |
| `city` | VARCHAR | 50 | NULL | NULL | City name |
| `country` | VARCHAR | 50 | NULL | NULL | Country name |
| `budget` | VARCHAR | 100 | NULL | NULL | Budget information |
| `amount` | DECIMAL(12,2) | - | NULL | NULL | Amount (with 2 decimal places) |
| `timeline` | VARCHAR | 100 | NULL | NULL | Decision Timeline |
| `tags` | VARCHAR | 200 | NULL | NULL | Comma-separated tags |
| `notes` | TEXT | - | NULL | NULL | Notes about the lead |

---

### Status Field

| Column Name | Data Type | Max Length | Nullable | Default | Description |
|------------|-----------|------------|----------|---------|-------------|
| `conversion_status` | VARCHAR | 20 | NULL | 'Pending' | Lead Status (Choices: Pending, Contacted, Qualified, Proposal, Negotiation, Won, Lost) |

---

### System Fields

| Column Name | Data Type | Nullable | Default | Description |
|------------|-----------|----------|---------|-------------|
| `created_at` | DATETIME | NOT NULL | Auto (Current Timestamp) | Record creation timestamp |
| `updated_at` | DATETIME | NOT NULL | Auto (Current Timestamp) | Record last update timestamp |
| `is_active` | BOOLEAN | NOT NULL | TRUE | Active status flag (used for soft delete) |

---

## Field Choices (Enums)

### Priority Choices
- `'Low'` - Low Priority
- `'Med'` - Medium Priority (Default)
- `'High'` - High Priority

### Source Choices
- `'Website'` - Website
- `'Referral'` - Referral
- `'Cold Call'` - Cold Call
- `'Social'` - Social Media
- `'Event'` - Event
- `'Other'` - Other

### Next Action Choices
- `'Call'` - Call
- `'Email'` - Email
- `'Demo'` - Demo
- `'Meeting'` - Meeting
- `'None'` - None (Default)

### Status Choices
- `'Pending'` - Pending (Default)
- `'Contacted'` - Contacted
- `'Qualified'` - Qualified
- `'Proposal'` - Proposal
- `'Negotiation'` - Negotiation
- `'Won'` - Won
- `'Lost'` - Lost

---

## Indexes

### Default Indexes
- **Primary Key Index**: `id` (Auto-created)
- **Foreign Key Indexes**: 
  - `assigned_to_id` (Auto-created by Django)
  - `imported_by_id` (Auto-created by Django)

### Custom Ordering
- **Default Ordering**: `-created_at` (Descending order by creation date)

---

## Relationships

### Foreign Key Relationships

1. **assigned_to** → `myapp_employee` table
   - Relationship: Many-to-One (Many Leads to One Employee)
   - Related Name: `assigned_leads`
   - On Delete: SET NULL (If employee deleted, lead's assigned_to becomes NULL)

2. **imported_by** → `myapp_employee` table
   - Relationship: Many-to-One (Many Leads to One Employee)
   - Related Name: `imported_leads`
   - On Delete: SET NULL (If employee deleted, lead's imported_by becomes NULL)

---

## Validation Rules

1. **Email Validation**: If email is provided, it must be a valid email format
2. **Phone Validation**: If phone is provided, it must match regex: `^[0-9+\-()\s]{7,20}$` (7-20 characters, digits, +, -, parentheses, spaces)
3. **Required Fields**: Either `email` OR `phone` must be provided (enforced in `clean()` method)
4. **Required Fields**: `name`, `source`, `owner`, `use_case` are mandatory

---

## Sample SQL CREATE Statement (PostgreSQL)

```sql
CREATE TABLE myapp_lead (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(254),
    phone VARCHAR(20),
    company VARCHAR(100),
    address TEXT,
    source VARCHAR(50) NOT NULL,
    priority VARCHAR(10) NOT NULL DEFAULT 'Med',
    owner VARCHAR(100) NOT NULL,
    use_case TEXT NOT NULL,
    next_action VARCHAR(20) DEFAULT 'None',
    due_date DATE,
    due_time TIME,
    website VARCHAR(200),
    industry VARCHAR(100),
    city VARCHAR(50),
    country VARCHAR(50),
    budget VARCHAR(100),
    amount DECIMAL(12,2),
    timeline VARCHAR(100),
    tags VARCHAR(200),
    notes TEXT,
    conversion_status VARCHAR(20) DEFAULT 'Pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    assigned_to_id INTEGER REFERENCES myapp_employee(id) ON DELETE SET NULL,
    imported_by_id INTEGER REFERENCES myapp_employee(id) ON DELETE SET NULL
);

-- Create indexes
CREATE INDEX idx_lead_assigned_to ON myapp_lead(assigned_to_id);
CREATE INDEX idx_lead_imported_by ON myapp_lead(imported_by_id);
CREATE INDEX idx_lead_created_at ON myapp_lead(created_at DESC);
CREATE INDEX idx_lead_is_active ON myapp_lead(is_active);
CREATE INDEX idx_lead_status ON myapp_lead(conversion_status);
```

---

## Important Notes

1. **Table Naming**: Django automatically creates table name as `app_name_model_name` (lowercase)
2. **Auto Fields**: `id`, `created_at`, `updated_at` are automatically managed by Django
3. **Soft Delete**: `is_active` field is used for soft delete (records are not physically deleted)
4. **Default Ordering**: Records are ordered by `-created_at` (newest first) by default
5. **Foreign Keys**: Both `assigned_to_id` and `imported_by_id` can be NULL (optional relationships)

---

## Data Fetching in Views

The `lead_get_data` view (line 3532 in `views.py`) fetches data using:
```python
lead = get_object_or_404(Lead, id=lead_id, is_active=True)
```

This means:
- Lead must exist with the given `id`
- Lead must have `is_active=True`
- If not found, returns 404 error

