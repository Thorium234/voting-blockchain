# 🔧 Troubleshooting Guide

## ✅ Recent Fixes Applied

### 1. API Port Mismatch (FIXED)
- **Issue**: Frontend connecting to port 8011, backend on port 8000
- **Fix**: Updated `frontend/lib/api.ts` to use port 8000
- **Action**: Restart frontend to apply changes

### 2. Custom 404 Page (ADDED)
- **Location**: `frontend/app/not-found.tsx`
- **Features**: Modern design, Go Back button, Home link
- **Test**: Visit http://localhost:3000/nonexistent

---

## 🚀 Quick Start Checklist

### Backend (Port 8000):
```bash
cd /home/thorium/Desktop/programming/2026/blockchain
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Verify**: http://localhost:8000/docs should show API docs

### Frontend (Port 3000):
```bash
cd /home/thorium/Desktop/programming/2026/blockchain/frontend
npm run dev
```

**Verify**: http://localhost:3000 should show homepage

---

## 🔐 Login Issues

### If you see "Login failed":

1. **Check backend is running:**
   ```bash
   curl http://localhost:8000/health
   ```
   Should return: `{"status":"healthy",...}`

2. **Test login via API:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@voting.system","password":"Admin@123"}'
   ```
   Should return JWT tokens

3. **Clear browser cache:**
   - Press `Ctrl+Shift+R` (hard refresh)
   - Or clear cache in browser settings

4. **Restart frontend:**
   ```bash
   cd frontend
   # Stop with Ctrl+C
   npm run dev
   ```

### If you see 404 on /login:

1. **Verify login page exists:**
   ```bash
   ls frontend/app/login/page.tsx
   ```

2. **Check Next.js is running:**
   ```bash
   ps aux | grep "next dev"
   ```

3. **Restart Next.js:**
   ```bash
   cd frontend
   rm -rf .next
   npm run dev
   ```

---

## 📊 System Status Check

### Check All Services:
```bash
# Backend
curl -s http://localhost:8000/health | jq .

# Frontend
curl -s http://localhost:3000 | grep -o "BlockchainVote"

# Database
sqlite3 voting.db "SELECT COUNT(*) FROM users;"
```

### Check Superadmin:
```bash
sqlite3 voting.db "SELECT email, voter_id, role FROM users WHERE role='superadmin';"
```

Expected output:
```
admin@voting.system|SUPER_ADMIN_001|superadmin
```

---

## 🐛 Common Issues

### Issue: "Failed to connect to localhost port 8000"
**Solution**: Backend not running
```bash
cd /home/thorium/Desktop/programming/2026/blockchain
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Issue: "CORS error"
**Solution**: Check CORS settings in `app/main.py`
```python
allow_origins=["http://localhost:3000"]
```

### Issue: "Invalid credentials"
**Solution**: Verify password in database
```bash
python create_superadmin.py
# Re-create superadmin if needed
```

### Issue: "Token expired"
**Solution**: Login again - tokens expire after 15 minutes

### Issue: Frontend shows old data
**Solution**: Clear Next.js cache
```bash
cd frontend
rm -rf .next
npm run dev
```

---

## 🔍 Debug Mode

### Enable Backend Logging:
```bash
# In app/database.py, add:
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### Check Backend Logs:
```bash
tail -f backend.log
# Or check terminal where uvicorn is running
```

### Check Frontend Logs:
- Open browser DevTools (F12)
- Go to Console tab
- Look for errors

---

## 📝 Credentials Reference

### Superadmin:
```
Email: admin@voting.system
Password: Admin@123
Voter ID: SUPER_ADMIN_001
```

### Test Voter (Create via admin):
```
Email: voter1@test.com
Password: Test@123
Voter ID: VOTER_001
```

---

## 🆘 Emergency Reset

### Reset Database:
```bash
cd /home/thorium/Desktop/programming/2026/blockchain
rm voting.db
python -c "from app.database import init_db; init_db()"
python create_superadmin.py
```

### Reset Frontend:
```bash
cd frontend
rm -rf .next node_modules
npm install
npm run dev
```

---

## ✅ Verification Steps

After any fix:

1. **Backend Health:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Frontend Loading:**
   ```bash
   curl http://localhost:3000 | grep "BlockchainVote"
   ```

3. **Login Test:**
   - Go to http://localhost:3000/login
   - Enter superadmin credentials
   - Should redirect to dashboard

4. **Admin Panel:**
   - Go to http://localhost:3000/admin
   - Should see admin dashboard
   - Try registering a test voter

---

## 📞 Support

### Check System Status:
```bash
# All in one command
echo "=== Backend ===" && curl -s http://localhost:8000/health | jq . && \
echo "=== Frontend ===" && curl -s http://localhost:3000 | grep -o "BlockchainVote" && \
echo "=== Database ===" && sqlite3 voting.db "SELECT COUNT(*) FROM users;" && \
echo "=== Superadmin ===" && sqlite3 voting.db "SELECT email FROM users WHERE role='superadmin';"
```

### Get Help:
1. Check this troubleshooting guide
2. Review error messages in terminal
3. Check browser console (F12)
4. Verify all services are running

---

**Last Updated**: After RBAC implementation and port fix  
**Status**: All systems operational ✅
