# Panduan Setup Cursor Automation (FIXED)

Buka: **https://cursor.com/automations**

Ada **2 automation** dengan jadwal berbeda:

| Automation | Jadwal | Cron |
|------------|--------|------|
| **Email Meeting Sync → Calendar** | **12 jam sekali** | `0 */12 * * *` |
| **EmailMeetingZoomLaunch** | **30 menit sekali** | `*/30 * * * *` |
| Meeting Start → Open Zoom (webhook) | Event-driven | Webhook (tetap) |

---

## Automation 1: Email Meeting Sync → Calendar (12 jam)

### Ubah di dashboard

1. Buka automation sync email Anda di https://cursor.com/automations
2. Edit **Trigger** → Scheduled → Custom cron:
   ```
   0 */12 * * *
   ```
   (= jam 00:00 dan 12:00 UTC)
3. Ganti **Instructions** dengan isi `PROMPT-01-email-sync.txt`
4. Save → pastikan **Active** ON

### Field lengkap

| Field | Nilai |
|-------|-------|
| **Name** | `Email Meeting Sync → Calendar` |
| **Trigger** | Scheduled → `0 */12 * * *` |
| **Repository** | No repository |
| **Tools** | MCP (Composio/Gmail+Calendar), Memories |
| **Active** | ON |

---

## Automation 2: EmailMeetingZoomLaunch (30 menit) — TETAP

### Ubah / buat di dashboard

1. Buka atau buat automation bernama **`EmailMeetingZoomLaunch`**
2. Trigger → Scheduled → Custom cron:
   ```
   */30 * * * *
   ```
   (= setiap 30 menit)
3. Ganti **Instructions** dengan isi `PROMPT-03-email-meeting-zoom-launch.txt`
4. Tools: MCP Calendar, Memories
5. Save → **Active** ON

### Field lengkap

| Field | Nilai |
|-------|-------|
| **Name** | `EmailMeetingZoomLaunch` |
| **Trigger** | Scheduled → `*/30 * * * *` |
| **Repository** | No repository |
| **Tools** | MCP (Google Calendar), Memories |
| **Active** | ON |

### Yang dikerjakan tiap 30 menit

- Cek Google Calendar (`yusuf.consultan@gmail.com`) untuk meeting dalam **35 menit ke depan**
- Jika ada Zoom/Meet/Teams link → kirim webhook ke Automation "Meeting Start → Open Zoom"
- Dedup via Memories agar tidak spam

---

## Automation 3: Meeting Start → Open Zoom (Webhook) — tetap

| Field | Nilai |
|-------|-------|
| **Name** | `Meeting Start → Open Zoom` |
| **ID** | `cdac76b4-8cc0-11f1-a7d1-d6b4613131ce` |
| **Trigger** | Webhook |
| **Active** | ON |

URL:
```
https://api2.cursor.sh/automations/webhook/cdac76b4-8cc0-11f1-a7d1-d6b4613131ce
```

---

## Google Apps Script — samakan ke 30 menit

Setelah update script, jalankan ulang `setupTriggers`.

Trigger: setiap **30 menit**, lihat meeting dalam **35 menit** ke depan (agar tidak miss).

Re-deploy Web App setelah paste script baru.

---

## Checklist fix

- [ ] Automation sync email: cron `0 */12 * * *`
- [ ] Automation `EmailMeetingZoomLaunch`: cron `*/30 * * * *`
- [ ] Prompt EmailMeetingZoomLaunch diganti (lihat PROMPT-03)
- [ ] Webhook automation Active
- [ ] Google Apps Script: `setupTriggers` ulang (interval 30 menit)
- [ ] Test: buka `.../exec?action=check`

## Alur

```
[Gmail x7] ──[Sync, tiap 12 jam]──► [Google Calendar]
                                           │
                    [EmailMeetingZoomLaunch, tiap 30 menit]
                                           │
                              meeting dalam 35 menit?
                                           │
                                           ▼
                         [Webhook → Meeting Start → Open Zoom]
                                           │
                                           ▼
                              [Local launcher / reminder]
```
