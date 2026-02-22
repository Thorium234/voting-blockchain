Blockchain-Based Voting System

Backend: FastAPI
Frontend: Next.js
Architecture: API-first, modular, security-focused

1. Project Overview
1.1 Vision

Build a secure, tamper-resistant blockchain-based voting system that:

Ensures vote integrity

Prevents double voting

Supports cryptographic verification

Enforces strict device control

Implements brute-force protection (IP banning)

Maintains auditability

The system will use a custom blockchain implementation (not Ethereum) built in Python with FastAPI.

2. High-Level Architecture
Next.js Frontend
        |
        v
FastAPI Backend (REST API)
        |
        v
Blockchain Engine (Core Module)
        |
        v
Database (User + Session + Metadata Storage)

3. Core System Components
3.1 Backend (FastAPI)

Modules:

auth/ → authentication & device control

blockchain/ → core blockchain logic

voting/ → vote transaction handling

security/ → rate limiting & IP banning

admin/ → admin-only operations

3.2 Frontend (Next.js)

Pages:

/register

/login

/dashboard

/vote

/results

/admin

Features:

JWT-based auth

Device-bound login enforcement

Real-time vote status updates

Admin monitoring dashboard

4. Blockchain Design
4.1 Block Structure

Each block contains:

{
    index: int,
    timestamp: datetime,
    votes: list[VoteTransaction],
    previous_hash: str,
    nonce: int,
    hash: str
}

4.2 Vote Transaction Structure
{
    voter_id: str,
    candidate_id: str,
    timestamp: datetime,
    signature: str (optional if using digital signatures)
}

4.3 Hashing

Use SHA-256 (hashlib)

Hash entire block contents

Link each block to previous block via previous_hash

4.4 Consensus (Simplified)

Since this is centralized:

Validate block hash

Ensure no duplicate voter IDs

Ensure valid digital signature (if enabled)

Verify previous hash consistency

No distributed mining required.

5. Voting Logic
5.1 User Registration

Options:

Basic Mode

Unique voter ID

Email + password

Stored securely (bcrypt hashing)

Advanced Mode (Recommended)

Generate public/private key pair

Store public key

User signs vote with private key

Server verifies using public key

5.2 Casting a Vote

Steps:

User authenticated

User selects candidate

Vote transaction created

Check:

User has not voted before

User is eligible

Signature valid (if using crypto)

Add vote to pending transactions

When threshold reached → create block

5.3 Prevent Double Voting

Mechanisms:

Database record has_voted flag

Blockchain scan verification

Unique constraint on voter ID

Signed vote verification

6. Security Architecture

This is critical.

6.1 Brute Force Protection (IP Ban)

Implement:

Rate limit login attempts

Track failed attempts per IP

If threshold exceeded:

Temporarily ban IP

Store in blacklist table

Automatic expiration after defined time

Implementation Options:

Middleware in FastAPI

Redis for rate limiting (recommended)

Store IP logs in database

6.2 Device Lock (MAC Address Binding)

Important Note:
Browsers cannot directly access MAC addresses for security reasons.

Instead:

Alternative Device Fingerprinting Strategy

Capture:

User Agent

Screen resolution

Timezone

Browser fingerprint hash

IP address

Store as device_fingerprint

Rules:

First login → device locked

Only admin can reset device

If login from different fingerprint → deny access

6.3 One Device Login Policy

Implement:

Single active session per user

On new login:

Invalidate previous JWT

Remove previous session record

Maintain active_session_id in database

6.4 JWT Authentication

Short-lived access token

Refresh token system

Store token version in DB

Increment token version on logout to invalidate old tokens

7. Cryptography
7.1 Hashing

Use:

hashlib.sha256()


For:

Block hashing

Fingerprint hashing

Integrity checks

7.2 Password Hashing

Use:

bcrypt or passlib

Never store raw passwords.

7.3 Optional Digital Signatures

Use:

ecdsa Python library

Flow:

User generates key pair

Signs vote with private key

Backend verifies with public key

8. Admin Features

Admin Capabilities:

Reset user device binding

Unban IP addresses

View blockchain

Validate chain integrity

Force block mining

View suspicious activity logs

9. Database Design

Tables:

Users

id

email

password_hash

public_key (optional)

has_voted

device_fingerprint

token_version

is_admin

Votes

id

voter_id

candidate_id

timestamp

block_index

Blocks

index

hash

previous_hash

nonce

timestamp

IPBlacklist

ip_address

banned_until

reason

10. API Endpoints (FastAPI)
Auth

POST /register

POST /login

POST /logout

Voting

POST /vote

GET /results

GET /blockchain

Admin

POST /admin/reset-device/{user_id}

POST /admin/unban-ip/{ip}

GET /admin/logs

11. Frontend Architecture (Next.js)
Authentication

Store access token securely

Handle token refresh

Auto logout on token invalidation

State Management

Use React context or Zustand

Protect routes

Admin-only routing

12. Project Phases
Phase 1 – Core Blockchain

Implement block structure

Implement hashing

Implement chain validation

Phase 2 – Voting Logic

User registration

Vote casting

Prevent double voting

Phase 3 – Security Layer

Rate limiting

IP banning

Device fingerprint locking

Single session enforcement

Phase 4 – Frontend

Auth pages

Voting UI

Admin dashboard

Phase 5 – Hardening

Logging

Audit trail

Chain verification tool

Unit tests

13. Potential Future Enhancements

Zero-knowledge proofs

Distributed nodes

Peer-to-peer syncing

Merkle trees for vote storage

End-to-end encrypted votes

14. Risks & Challenges

True voter anonymity vs auditability tradeoff

Device fingerprint reliability

Blockchain scalability

Replay attack protection

Session hijacking prevention

15. Definition of Done

The project is complete when:

Votes are immutable

No user can vote twice

Device locking works

IP banning works

One-device login enforced

Blockchain validates correctly

Admin can monitor everything

All endpoints protected
