# Automation 2: Meeting Reminder + Open Zoom (Webhook)

**Trigger:** Webhook
**Repository:** No repository
**Tools:** MCP server (meeting-automation), Send to Slack (opsional)

---

## Tujuan

Ketika waktu meeting tiba (dipicu oleh Google Apps Script atau scheduler eksternal), kirim reminder dan trigger pembukaan Zoom.

## Payload Webhook (contoh)

```json
{
  "event": "meeting_start",
  "title": "Interview Binus",
  "start": "2026-07-31T14:00:00+07:00",
  "url": "https://zoom.us/j/1234567890",
  "zoom_url": "https://zoom.us/j/1234567890",
  "location": "https://zoom.us/j/1234567890",
  "calendar_email": "yusuf.consultan@gmail.com"
}
```

## Langkah Eksekusi

1. Parse payload webhook.
2. Verifikasi event di calendar dengan `calendar_list_events` untuk email yusuf.consultan@gmail.com.
3. Ekstrak meeting URL (prioritas: zoom_url > url > location).
4. POST ke local webhook `http://localhost:8765` dengan payload yang sama untuk membuka Zoom di device user.
5. Jika Slack diaktifkan, kirim pesan:
   ```
   🔔 Meeting dimulai: {title}
   ⏰ {start}
   🔗 {meeting_url}
   ```
6. Jangan coba buka aplikasi di cloud VM — hanya trigger local webhook.

## Catatan

- Zoom account: yusuf.consultan@gmail.com
- Local webhook harus berjalan di device user (jalankan `python scripts/meeting_launcher.py`)
