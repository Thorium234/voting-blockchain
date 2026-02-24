# 🎯 SUPER ADMIN COMMAND CENTER

## Complete Election Management System

### **Core Features**

#### 1. **Election Wizard** - One-Click Setup
Create complete elections with multiple seats in one API call:

```bash
POST /api/v1/command-center/election/create-wizard
{
  "title": "General Election 2024",
  "description": "National elections",
  "seats": [
    {"name": "Presidential", "max_aspirants": 5},
    {"name": "Gubernatorial", "max_aspirants": 3},
    {"name": "Senate", "max_aspirants": 10}
  ]
}

Response:
{
  "election_id": "ELEC_A1B2C3D4",
  "seats": [
    {"seat_id": "SEAT_X1Y2Z3", "name": "Presidential", "max_aspirants": 5},
    {"seat_id": "SEAT_P4Q5R6", "name": "Gubernatorial", "max_aspirants": 3}
  ]
}
```

#### 2. **Seat-Based Aspirant Assignment**
Assign aspirants to specific seats:

```bash
POST /api/v1/command-center/election/{election_id}/seat/{seat_id}/assign-aspirants
{
  "aspirant_ids": ["CAND_001", "CAND_002", "CAND_003"]
}
```

#### 3. **Ballot Preview**
See exactly how voters will view the ballot:

```bash
GET /api/v1/command-center/election/{election_id}/ballot-preview

Response:
{
  "ballot": [
    {
      "seat_name": "Presidential",
      "aspirant_count": 5,
      "aspirants": [
        {"candidate_id": "CAND_001", "name": "John Doe", "party": "Party A"},
        {"candidate_id": "CAND_002", "name": "Jane Smith", "party": "Party B"}
      ]
    },
    {
      "seat_name": "Gubernatorial",
      "aspirant_count": 2,
      "aspirants": [...]
    }
  ]
}
```

#### 4. **Auto Voter ID Generation** - Cryptographic Minting
Generate secure voter IDs with blockchain addresses:

```bash
POST /api/v1/command-center/voter/mint-identity
{
  "email": "voter@example.com",
  "full_name": "Alice Johnson",
  "id_number": "ID123456",
  "phone": "+1234567890"
}

Response:
{
  "voter_id": "VA1B2C3D4E5",
  "blockchain_address": "0xabcdef1234567890...",
  "temp_password": "Vote12ab34cd!",
  "message": "Voter identity minted successfully"
}
```

**How It Works:**
- Voter ID: SHA-256 hash of email + name + timestamp (10 chars)
- Blockchain Address: SHA-256 of voter_id + timestamp (40 chars)
- One ID = One Vote (cryptographically bound)

#### 5. **Omniscient Admin Surveillance**
Real-time monitoring of all admin activities:

```bash
GET /api/v1/command-center/surveillance/admin-activity?hours=24

Response:
{
  "admins": [
    {
      "email": "admin@system.com",
      "role": "admin",
      "is_deletable": true,
      "last_login": "2024-01-15T14:30:00",
      "last_login_ip": "192.168.1.1",
      "is_online": true,
      "session_ip": "192.168.1.1",
      "recent_actions": [
        {
          "action": "register_voter",
          "details": "Registered 10 voters",
          "timestamp": "2024-01-15T14:35:00",
          "ip": "192.168.1.1"
        }
      ],
      "action_count_24h": 25
    }
  ]
}
```

#### 6. **Unauthorized Access Tracking**
Monitor failed attempts and suspicious activities:

```bash
GET /api/v1/command-center/surveillance/unauthorized-attempts

Response:
{
  "failed_logins": [
    {
      "email": "hacker@evil.com",
      "ip": "10.0.0.1",
      "timestamp": "2024-01-15T12:00:00"
    }
  ],
  "suspicious_activities": [
    {
      "user_id": 5,
      "action": "delete_admin",
      "details": "Attempted to delete superadmin",
      "ip": "10.0.0.2",
      "timestamp": "2024-01-15T13:00:00"
    }
  ]
}
```

#### 7. **System Health Dashboard**
Complete system status:

```bash
GET /api/v1/command-center/system/health-check

Response:
{
  "database": {
    "status": "healthy",
    "total_users": 1000,
    "total_voters": 950,
    "total_admins": 5
  },
  "blockchain": {
    "status": "healthy",
    "is_valid": true,
    "height": 25,
    "total_votes": 750
  },
  "security": {
    "active_sessions": 12,
    "banned_ips": 3
  },
  "elections": {
    "total": 2,
    "active": 1,
    "draft": 1
  }
}
```

#### 8. **Kill Switch** - Emergency Admin Lock
Immediately lock compromised admin accounts:

```bash
POST /api/v1/command-center/security/lock-admin/{admin_id}
{
  "reason": "Attempted unauthorized access to superadmin functions"
}

Response:
{
  "success": true,
  "message": "Admin locked immediately",
  "reason": "Attempted unauthorized access"
}
```

**What Happens:**
- Account locked for 365 days
- All active sessions terminated
- Token version incremented (invalidates all JWTs)
- Audit log created
- SNS alert sent to Super Admin (TODO)

---

## **Database Schema**

### ElectionSeats Table
```sql
CREATE TABLE election_seats (
    id INTEGER PRIMARY KEY,
    election_id INTEGER NOT NULL,
    seat_id VARCHAR(50) UNIQUE NOT NULL,
    seat_name VARCHAR(100) NOT NULL,
    seat_order INTEGER DEFAULT 0,
    max_aspirants INTEGER DEFAULT 10,
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME
);
```

### SeatAspirants Table
```sql
CREATE TABLE seat_aspirants (
    id INTEGER PRIMARY KEY,
    seat_id INTEGER NOT NULL,
    candidate_id INTEGER NOT NULL,
    position_order INTEGER DEFAULT 0,
    assigned_at DATETIME,
    assigned_by INTEGER NOT NULL
);
```

---

## **Complete Workflow**

### Step 1: Create Election with Seats
```bash
curl -X POST http://localhost:8000/api/v1/command-center/election/create-wizard \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "General Election 2024",
    "description": "National elections",
    "seats": [
      {"name": "Presidential", "max_aspirants": 5},
      {"name": "Gubernatorial", "max_aspirants": 3}
    ]
  }'
```

### Step 2: Register Aspirants
```bash
# Register aspirants (existing endpoint)
curl -X POST http://localhost:8000/api/v1/superadmin/candidate/register \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "John Doe", "party": "Party A"}'
```

### Step 3: Assign Aspirants to Seats
```bash
curl -X POST http://localhost:8000/api/v1/command-center/election/ELEC_XXX/seat/SEAT_YYY/assign-aspirants \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"aspirant_ids": ["CAND_001", "CAND_002", "CAND_003"]}'
```

### Step 4: Preview Ballot
```bash
curl -X GET http://localhost:8000/api/v1/command-center/election/ELEC_XXX/ballot-preview \
  -H "Authorization: Bearer $TOKEN"
```

### Step 5: Mint Voter Identities
```bash
curl -X POST http://localhost:8000/api/v1/command-center/voter/mint-identity \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "email": "voter@example.com",
    "full_name": "Alice Johnson",
    "id_number": "ID123456"
  }'
```

### Step 6: Open Polls
```bash
curl -X POST http://localhost:8000/api/v1/superadmin/election/ELEC_XXX/open-polls \
  -H "Authorization: Bearer $TOKEN"
```

### Step 7: Monitor Admin Activity
```bash
curl -X GET http://localhost:8000/api/v1/command-center/surveillance/admin-activity \
  -H "Authorization: Bearer $TOKEN"
```

### Step 8: Close Polls & Commit Results
```bash
curl -X POST http://localhost:8000/api/v1/superadmin/election/ELEC_XXX/close-polls \
  -H "Authorization: Bearer $TOKEN"

curl -X POST http://localhost:8000/api/v1/superadmin/election/ELEC_XXX/commit-results \
  -H "Authorization: Bearer $TOKEN"
```

---

## **Security Features**

### 1. **Immutable Super Admin**
- `is_deletable = False` in database
- Cannot be locked by Kill Switch
- Only superadmin can modify superadmin

### 2. **Cryptographic Voter IDs**
- SHA-256 based generation
- Unique per voter
- Blockchain address binding
- One ID = One Vote guarantee

### 3. **Real-Time Surveillance**
- All admin actions logged
- Last active tracking
- Online status monitoring
- IP address logging

### 4. **Kill Switch Protection**
- Immediate account lockdown
- Session termination
- Token invalidation
- Audit trail

---

## **Frontend UI Requirements**

### Super Admin Dashboard Layout
```
┌─────────────────────────────────────────────────────────┐
│  SUPER ADMIN COMMAND CENTER                    [Logout] │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Create       │  │ Mint Voter   │  │ Surveillance │  │
│  │ Election     │  │ Identity     │  │ Dashboard    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                           │
│  ┌───────────────────────────────────────────────────┐  │
│  │  ELECTION WIZARD                                   │  │
│  │  Step 1: Election Details                         │  │
│  │  Step 2: Define Seats (Presidential, Governor...) │  │
│  │  Step 3: Assign Aspirants to Seats               │  │
│  │  Step 4: Preview Ballot                           │  │
│  │  Step 5: Initialize Genesis Block                 │  │
│  └───────────────────────────────────────────────────┘  │
│                                                           │
│  ┌───────────────────────────────────────────────────┐  │
│  │  LIVE ADMIN SURVEILLANCE                           │  │
│  │  • Admin-John: Online (192.168.1.1) - 25 actions  │  │
│  │  • Admin-Mary: Offline - Last seen 2h ago         │  │
│  │  • Admin-Bob: LOCKED - Unauthorized attempt       │  │
│  └───────────────────────────────────────────────────┘  │
│                                                           │
│  ┌───────────────────────────────────────────────────┐  │
│  │  SYSTEM HEALTH                                     │  │
│  │  Database: ✅ | Blockchain: ✅ | Security: ✅     │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## **Installation**

```bash
# Run migration
python migrate_seats.py

# Clear cache
find . -type d -name __pycache__ -exec rm -rf {} +

# Restart backend
uvicorn app.main:app --reload --port 8000
```

---

## **API Endpoints Summary**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/command-center/election/create-wizard` | POST | Create election with seats |
| `/command-center/election/{id}/seat/{seat_id}/assign-aspirants` | POST | Assign aspirants to seat |
| `/command-center/election/{id}/ballot-preview` | GET | Preview voter ballot |
| `/command-center/voter/mint-identity` | POST | Generate voter ID + blockchain address |
| `/command-center/surveillance/admin-activity` | GET | Monitor all admin activities |
| `/command-center/surveillance/unauthorized-attempts` | GET | Track security threats |
| `/command-center/system/health-check` | GET | System status |
| `/command-center/security/lock-admin/{id}` | POST | Emergency admin lockdown |

---

**Status**: ✅ Backend Complete | 🔲 Frontend Pending
**Security**: Genesis Admin Protected | Kill Switch Enabled
**Blockchain**: Cryptographic Voter ID Binding
