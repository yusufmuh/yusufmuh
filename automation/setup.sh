#!/bin/bash
# Setup script for Meeting Automation
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  Meeting Automation Setup"
echo "  Email → Calendar → Zoom"
echo "=========================================="
echo ""

# Python venv
if [ ! -d ".venv" ]; then
    echo "[1/5] Creating Python virtual environment..."
    python3 -m venv .venv
else
    echo "[1/5] Virtual environment already exists."
fi

source .venv/bin/activate
echo "[2/5] Installing dependencies..."
pip install -q -r requirements.txt

# Directories
mkdir -p credentials/tokens data
echo "[3/5] Created credentials/ and data/ directories."

# .env
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "[4/5] Created .env from .env.example — edit as needed."
else
    echo "[4/5] .env already exists."
fi

# Check credentials
if [ ! -f "credentials/credentials.json" ]; then
    echo ""
    echo "⚠️  PERLU: Download credentials.json dari Google Cloud Console"
    echo "   Simpan di: automation/credentials/credentials.json"
    echo ""
    echo "   Langkah Google Cloud:"
    echo "   1. https://console.cloud.google.com → buat project baru"
    echo "   2. Enable APIs: Gmail API, Google Calendar API"
    echo "   3. OAuth consent screen → External → Publish (hindari expiry 7 hari)"
    echo "   4. Credentials → Create OAuth Client ID → Desktop app"
    echo "   5. Download JSON → rename ke credentials.json"
    echo ""
else
    echo "[5/5] credentials.json found ✓"
fi

echo ""
echo "=========================================="
echo "  Setup selesai! Langkah selanjutnya:"
echo "=========================================="
echo ""
echo "1. Hubungkan setiap akun Gmail (OAuth — bukan password):"
echo "   source .venv/bin/activate"
echo "   python scripts/connect_account.py"
echo ""
echo "2. Test sync email → calendar:"
echo "   python scripts/run_sync.py"
echo ""
echo "3. Jalankan meeting launcher (buka Zoom otomatis):"
echo "   python scripts/meeting_launcher.py"
echo ""
echo "4. Buat Cursor Automation:"
echo "   - Buka https://cursor.com/automations/new"
echo "   - Copy prompt dari cursor-automations/01-email-calendar-sync.md"
echo "   - Trigger: Scheduled (setiap 1 jam)"
echo ""
echo "5. Setup Google Apps Script untuk trigger meeting time:"
echo "   - Copy google-apps-script/meeting-trigger.gs ke script.google.com"
echo "   - Jalankan setupTriggers()"
echo ""
