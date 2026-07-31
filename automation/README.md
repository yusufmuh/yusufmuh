# Automation: Email → Google Calendar → Zoom

Sistem otomatis yang membaca email undangan meeting/interview dari **7 akun Gmail**, membuat event di **Google Calendar** (`yusuf.consultan@gmail.com`), dan **membuka Zoom** saat waktu meeting tiba.

## Arsitektur

```
┌─────────────────────────────────────────────────────────────┐
│  7 Akun Gmail (OAuth)                                       │
│  yusuf.consultan@gmail.com, binus, kuron, dll.              │
└──────────────────────┬──────────────────────────────────────┘
                       │ scan setiap jam
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Email Parser — deteksi undangan, .ics, link Zoom/Meet      │
└──────────────────────┬──────────────────────────────────────┘
                       │ create event
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Google Calendar (yusuf.consultan@gmail.com)                │
└──────────────────────┬──────────────────────────────────────┘
                       │ 2 menit sebelum meeting
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Google Apps Script → Cursor Webhook → Local Launcher       │
│  Membuka Zoom di device Anda                               │
└─────────────────────────────────────────────────────────────┘
```

## Setup Cepat

### 1. Install

```bash
cd automation
chmod +x setup.sh
./setup.sh
```

### 2. Google Cloud OAuth (sekali saja)

1. Buka https://console.cloud.google.com
2. Buat project → enable **Gmail API** + **Google Calendar API**
3. OAuth consent screen → External → **Publish**
4. Credentials → OAuth Client ID → **Desktop app**
5. Download JSON → simpan di `automation/credentials/credentials.json`

### 3. Hubungkan 7 Akun Gmail

**Penting:** Gunakan OAuth (bukan password). Jalankan untuk setiap akun:

```bash
source .venv/bin/activate
python scripts/connect_account.py
```

Pilih akun dari daftar, login di browser, grant permission. Ulangi 7 kali untuk semua akun.

### 4. Test Sync

```bash
python scripts/run_sync.py
```

### 5. Jalankan Meeting Launcher (buka Zoom otomatis)

```bash
python scripts/meeting_launcher.py
```

Service ini:
- Webhook di `http://localhost:8765` — terima trigger meeting
- Poll calendar setiap 60 detik — buka Zoom 2 menit sebelum meeting

### 6. Background Service (Linux)

```bash
chmod +x scripts/install-services.sh
./scripts/install-services.sh
```

### 7. Cursor Automation

1. Buka https://cursor.com/automations/new
2. **Automation 1 — Email Sync:**
   - Trigger: Scheduled (`0 * * * *` = setiap jam)
   - Repository: No repository
   - Tools: MCP server (meeting-automation)
   - Prompt: copy dari `cursor-automations/01-email-calendar-sync.md`
3. **Automation 2 — Meeting Zoom:**
   - Trigger: Webhook
   - Prompt: copy dari `cursor-automations/02-meeting-zoom-webhook.md`
   - Simpan webhook URL + token

### 8. Google Apps Script (trigger waktu meeting)

1. Buka https://script.google.com → project baru
2. Paste isi `google-apps-script/meeting-trigger.gs`
3. Ganti `CURSOR_WEBHOOK_URL` dan `CURSOR_WEBHOOK_TOKEN`
4. Jalankan fungsi `setupTriggers()` sekali
5. Authorize akses Calendar

## Akun yang Dimonitor

| Email | Nickname |
|-------|----------|
| yusuf.consultan@gmail.com | Primary calendar + Zoom |
| muhammad.yusuf010@binus.ac.id | Monitor |
| kuron.kursusonline@gmail.com | Monitor |
| muhammad.yusufbinbambang@gmail.com | Monitor |
| myustadzbambang@gmail.com | Monitor |
| yuukina99@gmail.com | Monitor |
| muhammad.yusuf010@edukator.elevaite.id | Monitor |

## MCP Tools (untuk Cursor Agent)

| Tool | Fungsi |
|------|--------|
| `accounts_list` | Daftar akun Gmail |
| `gmail_search` | Cari email meeting |
| `gmail_read_meeting` | Parse email jadi event |
| `calendar_list_events` | Lihat event mendatang |
| `calendar_create_event` | Buat event manual |
| `sync_emails_to_calendar` | Sync semua akun sekaligus |

## Deteksi Meeting

Email dianggap undangan meeting jika mengandung:
- Kata kunci: undangan, invitation, meeting, interview, wawancara, jadwal, zoom, webinar, rapat
- Link: zoom.us, meet.google.com, teams.microsoft.com
- Attachment: file `.ics` (iCalendar)

## Keamanan

- **Password email TIDAK disimpan** — hanya OAuth token
- Folder `credentials/` dan `data/` di-gitignore
- Token OAuth disimpan lokal di `credentials/tokens/`
- Jangan commit credentials ke repository

## Batasan

- Cursor Cloud Agent **tidak bisa** membuka Zoom di laptop Anda secara langsung
- Untuk buka Zoom di device, jalankan `meeting_launcher.py` di komputer Anda
- Gunakan ngrok/cloudflare tunnel jika ingin trigger remote ke local webhook
- Gmail API memerlukan OAuth — login password tidak didukung oleh Google

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| Token expired | Jalankan `connect_account.py` lagi |
| Event duplikat | File `data/processed_messages.json` track email yang sudah diproses |
| Zoom tidak terbuka | Pastikan `meeting_launcher.py` berjalan + Zoom app terinstall |
| 7-day token expiry | Publish OAuth consent screen di Google Cloud |
