# Blockchain-Based Voting System

A secure, tamper-resistant blockchain voting system built with FastAPI (backend) and Next.js (frontend). This system is designed for enterprise-grade security with defense-in-depth principles.

## ⚠️ Security Warning

**This is a high-risk, mission-critical system.** Treat it like a national election platform. Before production deployment:

1. Change all default secrets in `.env`
2. Configure proper CORS origins
3. Set up proper database (PostgreSQL recommended)
4. Enable TLS/SSL
5. Review all security configurations

---

## 🚀 Features

### Core Blockchain
- **Custom Blockchain** - Python-based with SHA-256 hashing
- **Merkle Root** - Cryptographic proof of vote integrity
- **Chain Checkpoints** - Efficient verification
- **Immutable Verification** - Tamper detection

### Security Hardening
- **Zero-Trust Auth** - JWT with IP/device binding
- **Sliding Window Rate Limiting** - Per-IP, per-user limits
- **Progressive IP Bans** - Soft throttle → temp ban → long ban
- **Anti-Replay Protection** - Nonce + timestamp validation
- **Hash-Chained Audit Logs** - Tamper-evident logging
- **Device Fingerprint Locking** - Bind accounts to devices
- **Single Session Policy** - One active login per user

### API Protection
- **Security Headers** - HSTS, CSP, X-Frame-Options
- **CORS Lockdown** - Explicit origins only
- **Request Size Limits** - Max body size enforcement

---

## 🏗️ Architecture

```
blockchain-voting/
├── app/
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # Configuration
│   ├── database.py                # Database setup
│   ├── models.py                  # SQLAlchemy models
│   ├── schemas.py                 # Pydantic schemas
│   ├── auth/                      # Authentication
│   │   ├── routes.py              # Auth endpoints
│   │   ├── jwt_handler.py         # JWT with zero-trust
│   │   ├── dependencies.py        # Auth dependencies
│   │   └── password.py            # Password hashing
│   ├── blockchain/                # Core blockchain
│   │   ├── block.py               # Block + Merkle root
│   │   └── chain.py               # Chain management
│   ├── voting/                    # Voting endpoints
│   │   └── routes.py              # Vote API
│   ├── security/                  # Security modules
│   │   ├── rate_limiter.py        # Sliding window limiter
│   │   ├── ip_ban.py              # IP banning
│   │   ├── anti_replay.py         # Nonce validation
│   │   └── audit_logging.py       # Hash-chained logs
│   └── admin/                     # Admin endpoints
│       └── routes.py              # Admin API
├── tests/                         # Unit tests
├── requirements.txt               # Python deps
└── README.md
```

---

## 📋 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new voter |
| POST | `/api/v1/auth/login` | Login (device-bound) |
| POST | `/api/v1/auth/logout` | Logout & invalidate tokens |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| GET | `/api/v1/auth/me` | Get current user |

### Voting
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/voting/vote` | Cast a vote |
| GET | `/api/v1/voting/results` | Get voting results |
| GET | `/api/v1/voting/blockchain` | View blockchain |
| GET | `/api/v1/voting/blockchain/validate` | Validate chain |
| GET | `/api/v1/voting/check-voted` | Check if voted |
| GET | `/api/v1/voting/vote-proof/{voter_id}` | Get vote merkle proof |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/users` | List users |
| POST | `/api/v1/admin/ban-ip` | Ban IP |
| POST | `/api/v1/admin/unban-ip/{ip}` | Unban IP |
| GET | `/api/v1/admin/banned-ips` | List banned IPs |
| GET | `/api/v1/admin/logs` | View audit logs |
| GET | `/api/v1/admin/security/stats` | Security statistics |

---

## 🔒 Security Details

### Rate Limiting
```
Auth endpoints: 5 requests/minute (per IP)
Vote endpoints: 10 requests/minute (per IP)
Admin endpoints: 30 requests/minute (per IP)
```

### Brute Force Protection
- **Soft throttle**: >5 failed attempts
- **Temporary ban**: >10 failed attempts (30 min)
- **Extended ban**: >20 failed attempts (2 hours)
- **Long ban**: >50 failed attempts (24 hours)

### JWT Security
- Access tokens: 15 minutes
- Refresh tokens: 7 days
- Token versioning for invalidation
- IP and device fingerprint binding

### Anti-Replay
- Cryptographic nonces (16+ chars)
- Timestamp validation (±5 minutes)
- One-time nonce recording in database
- Vote payload hashing before storage

### Audit Logging
- Hash-chained entries (tamper-evident)
- UTC timestamps
- IP address tracking
- Request ID tracing

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_blockchain.py -v
```

---

## ⚙️ Environment Variables

```env
# Server
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=sqlite:///./voting.db

# JWT (CHANGE IN PRODUCTION!)
SECRET_KEY=your-secret-key-change-in-production

# Security
RATE_LIMIT_AUTH_PER_MINUTE=5
RATE_LIMIT_VOTE_PER_MINUTE=10
MAX_LOGIN_ATTEMPTS=10
BAN_DURATION_MINUTES=30

# Zero Trust
BIND_TOKEN_TO_IP=true
BIND_TOKEN_TO_DEVICE=true
REQUIRE_DEVICE_FINGERPRINT=true

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
```

---

## 📝 Frontend TODO

For the Next.js frontend to work with this backend:

1. **Update API base URL** in `contexts/AuthContext.tsx`
2. **Add nonce endpoint** call before voting
3. **Update vote payload** to include nonce + timestamp
4. **Handle new error responses** (rate limit, IP banned)
5. **Add device fingerprint** generation
6. **Update auth flow** for new JWT structure

---

## 🔐 Security Checklist for Production

- [ ] Change `SECRET_KEY` to random 64+ character string
- [ ] Set `ALLOWED_ORIGINS` to exact frontend domain
- [ ] Switch to PostgreSQL database
- [ ] Enable TLS/SSL
- [ ] Configure HSTS
- [ ] Set up log aggregation
- [ ] Configure backup strategy
- [ ] Review admin access
- [ ] Test rate limiting
- [ ] Test IP banning
- [ ] Verify audit log chain
- [ ] Test chain validation
- [ ] Test vote merkle proofs

---

## 📄 License

MIT License
