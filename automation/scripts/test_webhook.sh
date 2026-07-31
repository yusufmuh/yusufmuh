#!/bin/bash
# Test Cursor Automation webhook
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
fi

URL="${CURSOR_WEBHOOK_URL:?Set CURSOR_WEBHOOK_URL in .env}"
TOKEN="${CURSOR_WEBHOOK_TOKEN:?Set CURSOR_WEBHOOK_TOKEN in .env}"

echo "Testing webhook: $URL"
echo ""

RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "meeting_start",
    "title": "Test Meeting - Automation Check",
    "start": "'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'",
    "url": "https://zoom.us/j/1234567890",
    "zoom_url": "https://zoom.us/j/1234567890",
    "location": "https://zoom.us/j/1234567890",
    "calendar_email": "yusuf.consultan@gmail.com"
  }')

BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')
STATUS=$(echo "$RESPONSE" | grep HTTP_STATUS | cut -d: -f2)

echo "HTTP Status: $STATUS"
echo "Response: $BODY"

if [ "$STATUS" = "200" ] || [ "$STATUS" = "202" ]; then
    echo ""
    echo "✓ Webhook berhasil! Cek run di https://cursor.com/agents"
    exit 0
else
    echo ""
    echo "✗ Webhook gagal. Periksa token dan pastikan automation Active."
    exit 1
fi
