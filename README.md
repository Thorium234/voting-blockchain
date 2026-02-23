# Blockchain-Based Voting System

A secure, tamper-resistant blockchain voting system built with FastAPI (backend) and designed for Next.js (frontend).

## Features

- **Custom Blockchain Implementation** - Python-based blockchain with SHA-256 hashing
- **Cryptographic Vote Verification** - Optional digital signatures using ECDSA
- **Double Voting Prevention** - Database + blockchain verification
- **Brute Force Protection** - IP banning with rate limiting
- **Device Fingerprint Locking** - Bind accounts to specific devices
- **Single Session Policy** - One active login per user
- **JWT Authentication** - Short-lived access tokens with refresh support
- **Admin Dashboard** - Chain validation, IP management, activity logs

## Tech Stack

- **Backend:** FastAPI
- **Database:** SQLite (SQLAlchemy ORM)
- **Authentication:** JWT (python-jose)
- **Password Hashing:** bcrypt
- **Cryptography:** ecdsa, hashlib

## Project Structure

```
blockchain-voting/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py           # Configuration settings
│   ├── database.py         # Database setup
│   ├── models.py           # SQLAlchemy models
│   ├── schemas.py          # Pydantic schemas
│   ├── auth/               # Authentication module
│   │   ├── __init__.py
│   │   ├── jwt_handler.py  # JWT handling
│   │   ├── password.py     # Password hashing
│   │   └── dependencies.py # Auth dependencies
│   ├── blockchain/          # Core blockchain logic
│   │   ├── __init__.py
│   │   ├── block.py        # Block structure
│   │   └── chain.py        # Blockchain management
│   ├── voting/              # Voting endpoints
│   │   ├── __init__.py
│   │   └── routes.py       # Vote API routes
│   ├── security/            # Security modules
│   │   ├── __init__.py
│   │   ├── rate_limiter.py # Rate limiting
│   │   ├── ip_ban.py      # IP banning
│   │   └── fingerprint.py  # Device fingerprinting
│   └── admin/              # Admin operations
│       ├── __init__.py
│       └── routes.py       # Admin API routes
├── tests/                  # Unit tests
├── requirements.txt        # Python dependencies
├── README.md
└── .env                   # Environment variables
```

## Installation

### Prerequisites

- Python 3.9+
- Node.js 18+ (for frontend)

### Backend Setup

```bash
# Clone and navigate to project
cd blockchain

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your settings

# Initialize database
python -m app.database

# Run the server
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Frontend Setup (Future)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new voter |
| POST | `/auth/login` | Login (device-bound) |
| POST | `/auth/logout` | Logout & invalidate tokens |
| POST | `/auth/refresh` | Refresh access token |

### Voting

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/vote` | Cast a vote |
| GET | `/results` | Get voting results |
| GET | `/blockchain` | View blockchain |
| GET | `/blockchain/validate` | Validate chain integrity |

### Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/admin/reset-device/{user_id}` | Reset user's device |
| POST | `/admin/unban-ip/{ip}` | Unban an IP |
| GET | `/admin/logs` | View activity logs |
| POST | `/admin/force-mine` | Force block mining |

## Blockchain Design

### Block Structure

```python
{
    "index": int,           # Block number
    "timestamp": datetime,  # Creation time
    "votes": [Vote],        # List of vote transactions
    "previous_hash": str,   # Hash of previous block
    "nonce": int,           # Proof value
    "hash": str             # Current block hash
}
```

### Vote Transaction

```python
{
    "voter_id": str,        # Unique voter identifier
    "candidate_id": str,    # Selected candidate
    "timestamp": datetime,  # Vote timestamp
    "signature": str        # Digital signature (optional)
}
```

### Consensus

Simplified proof-of-authority:
- Validate block hash (SHA-256)
- Check no duplicate voter IDs
- Verify previous hash link
- Optional: verify digital signatures

## Security Features

### 1. Brute Force Protection
- Rate limit: 5 attempts per minute
- IP ban after 10 failed attempts
- Automatic ban expiration (configurable)

### 2. Device Fingerprinting
- Captures: User-Agent, Screen resolution, Timezone, IP
- First login locks device
- Admin can reset device binding

### 3. Single Session Policy
- One active session per user
- New login invalidates previous JWT
- Stored session tracking in database

### 4. JWT Security
- Short-lived access tokens (15 min)
- Refresh tokens (7 days)
- Token version in DB for invalidation

## Database Schema

### Users Table
- id, email, password_hash, public_key
- has_voted, device_fingerprint, token_version
- is_admin, created_at

### Votes Table
- id, voter_id, candidate_id, timestamp
- block_index, transaction_hash

### Blocks Table
- index, hash, previous_hash, nonce
- timestamp, data

### IPBlacklist Table
- ip_address, banned_until, reason

## Development Phases

1. **Phase 1:** Core Blockchain (blocks, hashing, chain)
2. **Phase 2:** Voting Logic (registration, casting, prevention)
3. **Phase 3:** Security Layer (rate limiting, IP ban, device lock)
4. **Phase 4:** Frontend (auth pages, voting UI, admin dashboard)
5. **Phase 5:** Hardening (tests, logging, audit trail)

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/
```

## Environment Variables

```env
# Server
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=sqlite:///./voting.db

# JWT
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Security
MAX_LOGIN_ATTEMPTS=10
BAN_DURATION_MINUTES=30
RATE_LIMIT_PER_MINUTE=5
```

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request
