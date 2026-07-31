# Panduan Setup Cursor Automation

Buka: **https://cursor.com/automations/new**

Prasyarat:
- Paket Cursor **Pro** atau lebih tinggi
- MCP **Composio** sudah di-authenticate (Gmail + Google Calendar)
- OAuth Google sudah terhubung untuk akun `yusuf.consultan@gmail.com`

---

## Automation 1: Email → Google Calendar (Setiap Jam)

### Konfigurasi Field

| Field | Nilai |
|-------|-------|
| **Name** | `Email Meeting Sync → Calendar` |
| **Trigger** | Scheduled → Custom cron: `0 * * * *` |
| **Repository** | **No repository** |
| **Environment** | Cursor Cloud |
| **Model** | Claude Sonnet (atau model terbaik yang tersedia) |
| **Tools** | ✅ MCP Server (Composio), ✅ Memories |
| **Active** | ON setelah disimpan |

### Setup MCP (sekali saja)

1. Di halaman automation → **Tools** → **+ Add Tool or MCP**
2. **MCP Server** → **+ New Connection**
3. Cari **Composio** → Install → **Authenticate**
4. Hubungkan **Gmail** dan **Google Calendar** untuk akun `yusuf.consultan@gmail.com`
5. Ulangi authenticate untuk setiap akun Gmail tambahan jika Composio mendukung multi-account

### Instructions (copy-paste ke field Prompt)

```
Kamu adalah asisten yang memindahkan undangan meeting dari email ke Google Calendar.

## Akun Gmail yang dimonitor
1. yusuf.consultan@gmail.com (kalender utama)
2. muhammad.yusuf010@binus.ac.id
3. kuron.kursusonline@gmail.com
4. muhammad.yusufbinbambang@gmail.com
5. myustadzbambang@gmail.com
6. yuukina99@gmail.com
7. muhammad.yusuf010@edukator.elevaite.id

## Setiap run, lakukan:

### 1. Cek Memories
Baca daftar messageId/threadId email yang sudah diproses. Jangan proses ulang.

### 2. Cari email meeting (per akun)
Query Gmail:
in:inbox (subject:(undangan OR invitation OR invite OR meeting OR interview OR wawancara OR jadwal OR schedule OR zoom OR webinar OR rapat) OR "zoom.us" OR "meet.google.com" OR "teams.microsoft.com" OR has:attachment filename:ics) newer_than:1d

### 3. Parse setiap email baru
Ekstrak:
- Judul (dari subject)
- Waktu mulai & selesai (dari body atau attachment .ics)
- Link meeting: Zoom, Google Meet, atau Teams
- Peserta (dari To/Cc)
- Lokasi

### 4. Buat event di Google Calendar
Kalender target: yusuf.consultan@gmail.com (primary)

Sebelum buat, cek apakah event serupa sudah ada (judul + waktu ±30 menit).
Jika belum ada, buat event dengan:
- summary: judul email
- start/end: waktu yang terdeteksi (default 60 menit jika hanya waktu mulai)
- location: link Zoom/Meet/Teams
- description: ringkasan email + link asli
- timezone: Asia/Jakarta
- reminders: 10 menit dan 2 menit sebelum

### 5. Aturan
- Email dengan attachment .ics → parse dan buat event langsung
- Jika waktu tidak jelas → jangan buat event, catat untuk review manual
- Jika confidence rendah → lewati, jangan buat event palsu
- Setelah diproses → simpan messageId ke Memories

### 6. Output akhir
Ringkasan dalam bahasa Indonesia:
- Jumlah akun di-scan
- Jumlah email meeting ditemukan
- Jumlah event baru dibuat
- Daftar event (judul, waktu, link meeting)
- Error per akun jika ada
```

### Verifikasi

- Tunggu run pertama atau trigger manual
- Cek di https://cursor.com/agents
- Pastikan event muncul di Google Calendar `yusuf.consultan@gmail.com`

---

## Automation 2: Buka Zoom Saat Meeting (Webhook)

### Konfigurasi Field

| Field | Nilai |
|-------|-------|
| **Name** | `Meeting Start → Open Zoom` |
| **Trigger** | **Webhook** |
| **Repository** | **No repository** |
| **Environment** | Cursor Cloud |
| **Model** | Claude Sonnet |
| **Tools** | ✅ MCP Server (Composio), ✅ Memories |
| **Active** | ON setelah disimpan |

### Setelah Save — Ambil Webhook

1. **Save** automation dan aktifkan **Active**
2. Salin **Webhook URL** (format: `https://api2.cursor.sh/automations/webhook/<id>`)
3. Klik **Generate auth header** → salin token `Bearer crsr_...`
4. Simpan URL + token ke file `.env`:
   ```
   CURSOR_WEBHOOK_URL=https://api2.cursor.sh/automations/webhook/...
   CURSOR_WEBHOOK_TOKEN=crsr_...
   ```

### Instructions (copy-paste ke field Prompt)

```
Kamu menerima webhook saat waktu meeting tiba. Payload JSON ada di bagian bawah prompt ini.

## Langkah

1. Parse payload webhook:
   - event / type (default: meeting_start)
   - title / eventTitle / summary
   - start / startTime
   - url / meeting_url / zoom_url / location

2. Cek Memories — apakah reminder untuk event ini (title + start) sudah dikirim?
   Jika sudah → jawab "Already processed" dan stop.

3. Verifikasi di Google Calendar (yusuf.consultan@gmail.com):
   Gunakan MCP Calendar untuk cek event dengan judul dan waktu yang sama.

4. Ekstrak meeting URL (prioritas):
   zoom_url → url → location
   Harus berisi zoom.us, meet.google.com, atau teams.microsoft.com

5. Catat ke Memories: title, start, url, timestamp.

6. Output ringkasan:
   - Judul meeting
   - Waktu
   - Link meeting
   - Status: processed

## Penting
- JANGAN coba buka aplikasi di cloud VM
- Pembukaan Zoom dilakukan oleh local launcher di device user
- Payload tidak valid → laporkan error, jangan lanjut
```

### Test Webhook

```bash
curl -X POST "https://api2.cursor.sh/automations/webhook/<AUTOMATION-ID>" \
  -H "Authorization: Bearer crsr_<TOKEN-ANDA>" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "meeting_start",
    "title": "Test Interview Binus",
    "start": "2026-07-31T14:00:00+07:00",
    "url": "https://zoom.us/j/1234567890",
    "zoom_url": "https://zoom.us/j/1234567890",
    "calendar_email": "yusuf.consultan@gmail.com"
  }'
```

---

## Automation 3 (Opsional): Google Apps Script → Webhook

Agar webhook terpicu **tepat waktu meeting**, deploy script ini:

1. Buka https://script.google.com
2. Paste isi file `../google-apps-script/meeting-trigger.gs`
3. Ganti `CURSOR_WEBHOOK_URL` dan `CURSOR_WEBHOOK_TOKEN`
4. Jalankan fungsi `setupTriggers()` sekali
5. Authorize akses Google Calendar

Script ini cek calendar setiap 1 menit dan POST ke webhook Automation 2 saat meeting 2 menit lagi dimulai.

---

## Local Zoom Launcher (Device Anda)

Cursor Cloud **tidak bisa** membuka Zoom di laptop/HP Anda. Jalankan di komputer lokal:

```bash
cd automation
source .venv/bin/activate
python scripts/meeting_launcher.py
```

Script ini:
- Poll Google Calendar setiap 60 detik
- Buka Zoom/link meeting 2 menit sebelum waktu
- Webhook lokal di `http://localhost:8765`

Untuk trigger dari cloud ke device lokal, gunakan **ngrok**:
```bash
ngrok http 8765
```
Lalu masukkan URL ngrok ke `LOCAL_WEBHOOK_URL` di Google Apps Script.

---

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| MCP tidak muncul di automation | Setup MCP dari halaman automation, bukan hanya dari IDE |
| OAuth gagal | Re-authenticate Composio di dashboard automation |
| Webhook 401 | Regenerate auth header, pastikan `Bearer crsr_...` ada |
| Event duplikat | Pastikan Memories aktif |
| Zoom tidak terbuka | Jalankan `meeting_launcher.py` di device lokal |
| Cron salah waktu | Cron Cursor pakai UTC — sesuaikan offset |

## Diagram Alur

```
[Gmail x7] ──(setiap jam)──► [Automation 1: Email Sync]
                                      │
                                      ▼
                            [Google Calendar]
                                      │
                            (2 menit sebelum meeting)
                                      │
                                      ▼
                         [Google Apps Script trigger]
                                      │
                                      ▼
                         [Automation 2: Webhook]
                                      │
                          ┌───────────┴───────────┐
                          ▼                       ▼
               [Local meeting_launcher]    [Slack reminder]
                          │
                          ▼
                    [Buka Zoom App]
```
