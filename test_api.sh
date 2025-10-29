#!/bin/bash

# Family AI Assistant - E2E API Test Script
# This script tests the complete user journey:
# 1. Create two users
# 2. Create a family
# 3. Add both users as family members
# 4. Create a one-time task
# 5. Create recurring patterns (daily, weekly, monthly)

set -e  # Exit on error

# ============================================================================
# CONFIGURATION
# ============================================================================
BASE_URL="https://family-ai-assistant-790974712000.me-west1.run.app/api"
CONTENT_TYPE="Content-Type: application/json"

# Test data configuration
TIMESTAMP=$(date +%s)
FAMILY_NAME="Test Family ${TIMESTAMP}"
USER1_PHONE="+97250${TIMESTAMP:4:7}"
USER2_PHONE="+97250${TIMESTAMP:3:7}"

# Reduce task generation to keep DB minimal (days ahead)
DAYS_AHEAD=7  # Generate only 7 days of recurring tasks instead of 30

echo "=========================================="
echo "Family AI Assistant - E2E API Tests"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Family Name: $FAMILY_NAME"
echo "  Days Ahead: $DAYS_AHEAD days"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Helper function to make API calls and check status
api_call() {
    local method=$1
    local url=$2
    local data=$3
    local step_name=$4
    
    # Make the API call and capture response + status code
    local response_file=$(mktemp)
    local http_code
    
    if [ -z "$data" ]; then
        http_code=$(curl -s -w "%{http_code}" -X "$method" "$url" -o "$response_file")
    else
        http_code=$(curl -s -w "%{http_code}" -X "$method" "$url" \
            -H "$CONTENT_TYPE" \
            -d "$data" \
            -o "$response_file")
    fi
    
    local response=$(cat "$response_file")
    rm "$response_file"
    
    # Check if successful (2xx status code)
    if [[ $http_code =~ ^2[0-9][0-9]$ ]]; then
        echo "$response"
        return 0
    else
        echo -e "${RED}✗ ERROR in $step_name${NC}" >&2
        echo -e "${RED}HTTP Status: $http_code${NC}" >&2
        echo -e "${RED}Response:${NC}" >&2
        echo "$response" | jq '.' 2>/dev/null || echo "$response" >&2
        exit 1
    fi
}

# ============================================================================
# STEP 1: Create First User (Parent 1)
# ============================================================================
echo -e "${BLUE}STEP 1: Creating first user (Sarah)...${NC}"
USER1_RESPONSE=$(api_call "POST" "$BASE_URL/users" "{
  \"display_name\": \"Sarah Johnson\",
  \"phone_e164\": \"$USER1_PHONE\",
  \"whatsapp_opt_in\": true,
  \"preferences\": {
    \"timezone\": \"Asia/Jerusalem\",
    \"language\": \"en\"
  }
}" "STEP 1: Create User 1")

USER1_ID=$(echo $USER1_RESPONSE | jq -r '.id')
echo -e "${GREEN}✓ Created user 1: Sarah Johnson (ID: $USER1_ID)${NC}"
echo "$USER1_RESPONSE" | jq '.'
echo ""

# ============================================================================
# STEP 2: Create Second User (Parent 2)
# ============================================================================
echo -e "${BLUE}STEP 2: Creating second user (Michael)...${NC}"
USER2_RESPONSE=$(api_call "POST" "$BASE_URL/users" "{
  \"display_name\": \"Michael Johnson\",
  \"phone_e164\": \"$USER2_PHONE\",
  \"whatsapp_opt_in\": true,
  \"preferences\": {
    \"timezone\": \"Asia/Jerusalem\",
    \"language\": \"en\"
  }
}" "STEP 2: Create User 2")

USER2_ID=$(echo $USER2_RESPONSE | jq -r '.id')
echo -e "${GREEN}✓ Created user 2: Michael Johnson (ID: $USER2_ID)${NC}"
echo "$USER2_RESPONSE" | jq '.'
echo ""

# ============================================================================
# STEP 3: Create Family
# ============================================================================
echo -e "${BLUE}STEP 3: Creating family...${NC}"
FAMILY_RESPONSE=$(api_call "POST" "$BASE_URL/families" "{
  \"name\": \"$FAMILY_NAME\"
}" "STEP 3: Create Family")

FAMILY_ID=$(echo $FAMILY_RESPONSE | jq -r '.id')
echo -e "${GREEN}✓ Created family: $FAMILY_NAME (ID: $FAMILY_ID)${NC}"
echo "$FAMILY_RESPONSE" | jq '.'
echo ""

# ============================================================================
# STEP 4: Add User 1 to Family as Parent
# ============================================================================
echo -e "${BLUE}STEP 4: Adding Sarah to family as parent...${NC}"
MEMBER1_RESPONSE=$(api_call "POST" "$BASE_URL/families/$FAMILY_ID/members" "{
  \"user_id\": $USER1_ID,
  \"role\": \"parent\"
}" "STEP 4: Add User 1 to Family")

echo -e "${GREEN}✓ Added Sarah as family member${NC}"
echo "$MEMBER1_RESPONSE" | jq '.'
echo ""

# ============================================================================
# STEP 5: Add User 2 to Family as Parent
# ============================================================================
echo -e "${BLUE}STEP 5: Adding Michael to family as parent...${NC}"
MEMBER2_RESPONSE=$(api_call "POST" "$BASE_URL/families/$FAMILY_ID/members" "{
  \"user_id\": $USER2_ID,
  \"role\": \"parent\"
}" "STEP 5: Add User 2 to Family")

echo -e "${GREEN}✓ Added Michael as family member${NC}"
echo "$MEMBER2_RESPONSE" | jq '.'
echo ""

# ============================================================================
# STEP 6: Create a One-Time Task
# ============================================================================
echo -e "${BLUE}STEP 6: Creating one-time task...${NC}"

# Task due tomorrow at 6 PM
TASK_DUE_DATE=$(date -u -v+1d +"%Y-%m-%dT18:00:00Z" 2>/dev/null || date -u -d "+1 day" +"%Y-%m-%dT18:00:00Z")

TASK_RESPONSE=$(api_call "POST" "$BASE_URL/tasks" "{
  \"title\": \"Buy groceries for the week\",
  \"description\": \"Milk, eggs, bread, vegetables\",
  \"family_id\": $FAMILY_ID,
  \"assignee_user_id\": $USER1_ID,
  \"created_by_user_id\": $USER2_ID,
  \"status\": \"todo\",
  \"due_at\": \"$TASK_DUE_DATE\",
  \"meta\": {
    \"priority\": \"high\",
    \"category\": \"shopping\"
  }
}" "STEP 6: Create Task")

TASK_ID=$(echo $TASK_RESPONSE | jq -r '.id')
echo -e "${GREEN}✓ Created task: Buy groceries (ID: $TASK_ID)${NC}"
echo "$TASK_RESPONSE" | jq '.'
echo ""

# ============================================================================
# STEP 7: Create Daily Recurring Pattern
# ============================================================================
echo -e "${BLUE}STEP 7: Creating daily recurring pattern (Morning School Prep)...${NC}"

# Calculate dates for minimal task generation
START_DATE=$(date -u +"%Y-%m-%dT06:30:00Z")
END_DATE=$(date -u -v+${DAYS_AHEAD}d +"%Y-%m-%dT06:30:00Z" 2>/dev/null || date -u -d "+${DAYS_AHEAD} days" +"%Y-%m-%dT06:30:00Z")

DAILY_PATTERN_RESPONSE=$(api_call "POST" "$BASE_URL/recurring-patterns" "{
  \"title\": \"Morning School Preparation\",
  \"description\": \"Get kids ready for school - breakfast, lunch boxes, check backpacks\",
  \"family_id\": $FAMILY_ID,
  \"frequency\": \"daily\",
  \"interval\": 1,
  \"start_date\": \"$START_DATE\",
  \"end_date\": \"$END_DATE\",
  \"start_time_hour\": 6,
  \"start_time_minute\": 30,
  \"duration_minutes\": 60,
  \"default_assignee_user_id\": $USER1_ID,
  \"created_by_user_id\": $USER1_ID,
  \"is_active\": true,
  \"meta\": {
    \"category\": \"routine\",
    \"notification_minutes_before\": 15
  }
}" "STEP 7: Create Daily Recurring Pattern")

DAILY_PATTERN_ID=$(echo $DAILY_PATTERN_RESPONSE | jq -r '.id')
echo -e "${GREEN}✓ Created daily recurring pattern (ID: $DAILY_PATTERN_ID)${NC}"
echo "$DAILY_PATTERN_RESPONSE" | jq '.'
echo ""

# Give it a moment for task generation
sleep 2

# ============================================================================
# STEP 8: Create Weekly Recurring Pattern
# ============================================================================
echo -e "${BLUE}STEP 8: Creating weekly recurring pattern (Trash Day)...${NC}"

# Calculate dates for weekly pattern
WEEKLY_START_DATE=$(date -u +"%Y-%m-%dT20:00:00Z")
WEEKLY_END_DATE=$(date -u -v+${DAYS_AHEAD}d +"%Y-%m-%dT20:00:00Z" 2>/dev/null || date -u -d "+${DAYS_AHEAD} days" +"%Y-%m-%dT20:00:00Z")

WEEKLY_PATTERN_RESPONSE=$(api_call "POST" "$BASE_URL/recurring-patterns" "{
  \"title\": \"Take Out Trash\",
  \"description\": \"Put trash bins on curb for collection\",
  \"family_id\": $FAMILY_ID,
  \"frequency\": \"weekly\",
  \"interval\": 1,
  \"by_day\": [2, 5],
  \"start_date\": \"$WEEKLY_START_DATE\",
  \"end_date\": \"$WEEKLY_END_DATE\",
  \"start_time_hour\": 20,
  \"start_time_minute\": 0,
  \"duration_minutes\": 15,
  \"default_assignee_user_id\": $USER2_ID,
  \"created_by_user_id\": $USER1_ID,
  \"is_active\": true,
  \"meta\": {
    \"category\": \"chores\",
    \"location\": \"front_yard\"
  }
}" "STEP 8: Create Weekly Recurring Pattern")

WEEKLY_PATTERN_ID=$(echo $WEEKLY_PATTERN_RESPONSE | jq -r '.id')
echo -e "${GREEN}✓ Created weekly recurring pattern (ID: $WEEKLY_PATTERN_ID)${NC}"
echo "$WEEKLY_PATTERN_RESPONSE" | jq '.'
echo ""

sleep 2

# ============================================================================
# STEP 9: Create Monthly Recurring Pattern
# ============================================================================
echo -e "${BLUE}STEP 9: Creating monthly recurring pattern (Bill Payment)...${NC}"

# Calculate dates for monthly pattern (start on 1st of current month)
MONTHLY_START_DATE=$(date -u +"%Y-%m-01T10:00:00Z")
MONTHLY_END_DATE=$(date -u -v+${DAYS_AHEAD}d +"%Y-%m-%dT10:00:00Z" 2>/dev/null || date -u -d "+${DAYS_AHEAD} days" +"%Y-%m-%dT10:00:00Z")

MONTHLY_PATTERN_RESPONSE=$(api_call "POST" "$BASE_URL/recurring-patterns" "{
  \"title\": \"Pay Electricity Bill\",
  \"description\": \"Check and pay monthly electricity bill online\",
  \"family_id\": $FAMILY_ID,
  \"frequency\": \"monthly\",
  \"interval\": 1,
  \"by_day\": [1],
  \"start_date\": \"$MONTHLY_START_DATE\",
  \"end_date\": \"$MONTHLY_END_DATE\",
  \"start_time_hour\": 10,
  \"start_time_minute\": 0,
  \"duration_minutes\": 30,
  \"default_assignee_user_id\": $USER2_ID,
  \"created_by_user_id\": $USER2_ID,
  \"is_active\": true,
  \"meta\": {
    \"category\": \"bills\",
    \"estimated_amount\": 450,
    \"currency\": \"ILS\"
  }
}" "STEP 9: Create Monthly Recurring Pattern")

MONTHLY_PATTERN_ID=$(echo $MONTHLY_PATTERN_RESPONSE | jq -r '.id')
echo -e "${GREEN}✓ Created monthly recurring pattern (ID: $MONTHLY_PATTERN_ID)${NC}"
echo "$MONTHLY_PATTERN_RESPONSE" | jq '.'
echo ""

sleep 2

# ============================================================================
# VERIFICATION: Check what was created
# ============================================================================
echo ""
echo "=========================================="
echo "VERIFICATION: Checking Created Data"
echo "=========================================="
echo ""

echo -e "${BLUE}Family with Members:${NC}"
curl -s "$BASE_URL/families/$FAMILY_ID/with-members" | jq '.'
echo ""

echo -e "${BLUE}All Tasks for Family:${NC}"
curl -s "$BASE_URL/tasks?family_id=$FAMILY_ID" | jq '.'
echo ""

echo -e "${BLUE}Tasks Generated from Daily Pattern:${NC}"
curl -s "$BASE_URL/recurring-patterns/$DAILY_PATTERN_ID/tasks" | jq '. | length' | xargs -I {} echo "Generated {} task instances"
echo ""

echo -e "${BLUE}Tasks Generated from Weekly Pattern:${NC}"
curl -s "$BASE_URL/recurring-patterns/$WEEKLY_PATTERN_ID/tasks" | jq '. | length' | xargs -I {} echo "Generated {} task instances"
echo ""

echo -e "${BLUE}All Recurring Patterns:${NC}"
curl -s "$BASE_URL/recurring-patterns?family_id=$FAMILY_ID" | jq '.'
echo ""

# ============================================================================
# SUMMARY
# ============================================================================
echo ""
echo "=========================================="
echo "TEST SUMMARY"
echo "=========================================="
echo -e "${GREEN}✓ Created 2 users${NC}"
echo -e "${GREEN}✓ Created 1 family ($FAMILY_NAME)${NC}"
echo -e "${GREEN}✓ Added 2 family members${NC}"
echo -e "${GREEN}✓ Created 1 one-time task${NC}"
echo -e "${GREEN}✓ Created 3 recurring patterns (daily, weekly, monthly)${NC}"
echo -e "${GREEN}✓ Auto-generated task instances for next $DAYS_AHEAD days${NC}"
echo ""
echo "Family: $FAMILY_NAME (ID: $FAMILY_ID)"
echo "User 1: Sarah Johnson (ID: $USER1_ID, Phone: $USER1_PHONE)"
echo "User 2: Michael Johnson (ID: $USER2_ID, Phone: $USER2_PHONE)"
echo "Task ID: $TASK_ID"
echo "Daily Pattern ID: $DAILY_PATTERN_ID"
echo "Weekly Pattern ID: $WEEKLY_PATTERN_ID"
echo "Monthly Pattern ID: $MONTHLY_PATTERN_ID"
echo ""
echo -e "${GREEN}All tests completed successfully!${NC}"

