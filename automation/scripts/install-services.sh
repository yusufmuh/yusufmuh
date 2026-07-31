#!/bin/bash
# Install systemd services for background automation (Linux)
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
USER_NAME="${SUDO_USER:-$USER}"
HOME_DIR=$(eval echo "~$USER_NAME")

echo "Installing systemd services for $USER_NAME..."

# Email sync service (every 12 hours via timer)
cat > /tmp/email-calendar-sync.service << EOF
[Unit]
Description=Email to Calendar Sync
After=network.target

[Service]
Type=oneshot
User=$USER_NAME
WorkingDirectory=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/.venv/bin/python $SCRIPT_DIR/scripts/run_sync.py
Environment=PATH=$SCRIPT_DIR/.venv/bin:/usr/bin

[Install]
WantedBy=multi-user.target
EOF

cat > /tmp/email-calendar-sync.timer << EOF
[Unit]
Description=Run email-calendar sync every 12 hours

[Timer]
OnCalendar=00,12:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Meeting launcher service (always running)
cat > /tmp/meeting-launcher.service << EOF
[Unit]
Description=Meeting Launcher Webhook + Calendar Poll
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/.venv/bin/python $SCRIPT_DIR/scripts/meeting_launcher.py
Restart=always
RestartSec=10
Environment=PATH=$SCRIPT_DIR/.venv/bin:/usr/bin

[Install]
WantedBy=multi-user.target
EOF

sudo cp /tmp/email-calendar-sync.service /etc/systemd/system/
sudo cp /tmp/email-calendar-sync.timer /etc/systemd/system/
sudo cp /tmp/meeting-launcher.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable email-calendar-sync.timer
sudo systemctl enable meeting-launcher.service
sudo systemctl start email-calendar-sync.timer
sudo systemctl start meeting-launcher.service

echo ""
echo "Services installed:"
echo "  email-calendar-sync.timer  — sync setiap 12 jam"
echo "  meeting-launcher.service   — webhook + auto-open Zoom"
echo ""
echo "Status:"
sudo systemctl status email-calendar-sync.timer --no-pager || true
sudo systemctl status meeting-launcher.service --no-pager || true
