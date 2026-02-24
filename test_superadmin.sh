#!/bin/bash

# Super Admin Dashboard Test Script

BASE_URL="http://localhost:8000/api/v1"
SUPERADMIN_EMAIL="admin@voting.system"
SUPERADMIN_PASSWORD="Admin@123"

echo "🔐 Testing Super Admin Dashboard Endpoints"
echo "=========================================="

# 1. Login as superadmin
echo -e "\n1️⃣  Logging in as superadmin..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$SUPERADMIN_EMAIL\",\"password\":\"$SUPERADMIN_PASSWORD\"}")

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "❌ Login failed"
    echo $LOGIN_RESPONSE
    exit 1
fi

echo "✅ Login successful"

# 2. Initialize Genesis Block
echo -e "\n2️⃣  Initializing genesis block..."
curl -s -X POST "$BASE_URL/superadmin/election/initialize-genesis" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "election_id": "TEST_ELECTION_2024",
    "title": "Test General Election 2024",
    "description": "Testing election lifecycle"
  }' | jq '.'

# 3. Register Candidate
echo -e "\n3️⃣  Registering candidate..."
CANDIDATE_RESPONSE=$(curl -s -X POST "$BASE_URL/superadmin/candidate/register" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "party": "Independent Party",
    "manifesto": "Education and healthcare reform"
  }')

echo $CANDIDATE_RESPONSE | jq '.'
CANDIDATE_ID=$(echo $CANDIDATE_RESPONSE | grep -o '"candidate_id":"[^"]*' | cut -d'"' -f4)

# 4. Certify Candidate
if [ ! -z "$CANDIDATE_ID" ]; then
    echo -e "\n4️⃣  Certifying candidate..."
    curl -s -X POST "$BASE_URL/superadmin/candidate/$CANDIDATE_ID/certify" \
      -H "Authorization: Bearer $TOKEN" | jq '.'
fi

# 5. Register Voter
echo -e "\n5️⃣  Registering voter with flexible fields..."
curl -s -X POST "$BASE_URL/superadmin/voter/register" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testvoter@example.com",
    "password": "Voter@123",
    "full_name": "Jane Smith",
    "id_number": "ID123456",
    "reg_number": "REG789",
    "phone": "+1234567890",
    "custom_fields": {
      "department": "Engineering",
      "year": "2024"
    }
  }' | jq '.'

# 6. Open Polls
echo -e "\n6️⃣  Opening polls..."
curl -s -X POST "$BASE_URL/superadmin/election/TEST_ELECTION_2024/open-polls" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# 7. Get Activity Feed
echo -e "\n7️⃣  Fetching activity feed..."
curl -s -X GET "$BASE_URL/superadmin/activity-feed?hours=1&limit=10" \
  -H "Authorization: Bearer $TOKEN" | jq '.activities | .[:3]'

# 8. Get Analytics Dashboard
echo -e "\n8️⃣  Fetching analytics dashboard..."
curl -s -X GET "$BASE_URL/superadmin/analytics/dashboard" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# 9. List Admins
echo -e "\n9️⃣  Listing all admins..."
curl -s -X GET "$BASE_URL/superadmin/admins" \
  -H "Authorization: Bearer $TOKEN" | jq '.admins'

# 10. List Candidates
echo -e "\n🔟 Listing candidates..."
curl -s -X GET "$BASE_URL/superadmin/candidates" \
  -H "Authorization: Bearer $TOKEN" | jq '.candidates'

echo -e "\n✅ All tests completed!"
echo "=========================================="
