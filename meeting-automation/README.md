# Meeting Email → Google Calendar → Zoom Automation

Otomatis memindai Gmail, mendeteksi undangan/meeting/interview/Zoom/Meet, menulis acara ke Google Calendar, lalu membuka Zoom saat waktunya tiba.

## Keamanan (WAJIB BACA)

**Jangan pernah menyimpan password Gmail di repo, chat, atau file `.env`.**

Jika Anda baru saja membagikan password akun di chat/issue:

1. **Ganti semua password itu sekarang** di Google Account + akun kampus/kerja.
2. Aktifkan **2-Step Verification**.
3. Pakai **OAuth** (cara di bawah) — bukan login password.

Composio / Notion MCP di environment cloud ini belum terautentikasi. Automation ini berjalan **lokal di komputer Anda** (wajib untuk membuka Zoom di device Anda).

## Yang dilakukan

1. **Scan** 7 akun Gmail (konfigurasi di `config.yaml`)
2. **Deteksi** email berisi: undangan, meeting, interview, jadwal, kalender, Zoom, Google Meet, Teams, Webex, ICS, dll.
3. **Buat/update** event di Google Calendar akun target (`yusuf.consultan@gmail.com` by default)
4. **Saat hampir mulai** (±2 menit): buka link Zoom lewat app Zoom (`zoommtg://`) jika tersedia, atau browser

## Batasan penting

| Fitur | Status |
|---|---|
| Baca email + buat agenda Calendar | Ya (OAuth) |
| Buka Zoom di **PC yang menjalankan script** | Ya |
| Paksa buka Zoom di **semua device** (HP, laptop lain) | Tidak — pasang script/`watch` di tiap PC, atau andalkan notifikasi Google Calendar di HP |
| Login pakai password akun | **Tidak didukung** (tidak aman & diblokir Google) |

## Setup (sekali)

### 1. Python

```bash
cd meeting-automation
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Google Cloud OAuth client

1. Buka [Google Cloud Console](https://console.cloud.google.com/)
2. Buat project → aktifkan **Gmail API** + **Google Calendar API**
3. OAuth consent screen → External (atau Internal jika Workspace) → tambahkan scope:
   - `.../auth/gmail.readonly`
   - `.../auth/calendar`
4. Credentials → **Create OAuth client ID** → Application type **Desktop app**
5. Download JSON → simpan sebagai `meeting-automation/credentials.json`
6. Tambahkan semua alamat email Anda sebagai **Test users** (jika app masih Testing)

### 3. Authorize tiap akun

Di mesin lokal (butuh browser):

```bash
python scripts/auth_setup.py
# atau satu per satu:
python scripts/auth_setup.py --email yusuf.consultan@gmail.com
```

Login dengan akun yang diminta. Token disimpan di `tokens/` (sudah di-gitignore).

Akun di `config.yaml`:

- yusuf.consultan@gmail.com
- muhammad.yusuf010@binus.ac.id
- kuron.kursusonline@gmail.com
- muhammad.yusufbinbambang@gmail.com
- myustadzbambang@gmail.com
- yuukina99@gmail.com
- muhammad.yusuf010@edukator.elevaite.id

### 4. Jalankan

```bash
# Dry-run: parse saja
python -m src sync --dry-run

# Tulis ke Google Calendar
python -m src sync

# Continuous: sync email + buka Zoom saat due
python -m src watch

# Cek meeting yang hampir mulai (sekali)
python -m src open-due
```

## Menjalankan otomatis di PC (agar Zoom selalu kebuka)

### Linux (systemd user service)

Buat `~/.config/systemd/user/meeting-automation.service`:

```ini
[Unit]
Description=Meeting email calendar + Zoom opener
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/ABSOLUTE/PATH/meeting-automation
ExecStart=/ABSOLUTE/PATH/meeting-automation/.venv/bin/python -m src watch
Restart=always
RestartSec=30

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now meeting-automation.service
```

### Windows Task Scheduler / macOS launchd

Jadwalkan `python -m src watch` agar jalan saat login. Pastikan Zoom desktop terpasang dan sudah login (mis. dengan `yusuf.consultan@gmail.com`).

## Perintah lain

```bash
python -m src sync --email yuukina99@gmail.com --lookback 30
python -m src sync --force          # proses ulang
python -m src auth --email ...
```

## Struktur

```
meeting-automation/
  config.yaml          # akun + keyword
  credentials.json     # OAuth client (Anda yang taruh, tidak di-commit)
  tokens/              # token per akun (lokal)
  src/
    gmail_client.py
    meeting_parser.py
    calendar_client.py
    zoom_launcher.py
    main.py
```

## Tips Zoom

- Install **Zoom desktop** dan login sekali.
- Deep link `zoommtg://` dipakai jika URL Zoom valid; kalau handler tidak ada, fallback ke browser.
- Notifikasi Calendar di Android/iOS tetap berguna sebagai backup di HP.
