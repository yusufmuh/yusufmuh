# Automation: EmailMeetingZoomLaunch (Setiap 30 Menit)

**Name:** `EmailMeetingZoomLaunch`  
**Trigger:** Scheduled — `*/30 * * * *` (**TETAP 30 menit**)  
**Repository:** No repository  
**Tools:** MCP Google Calendar, Memories

---

## Tujuan

Setiap 30 menit, cek Google Calendar untuk meeting dalam 35 menit ke depan. Jika ada link Zoom/Meet/Teams, kirim webhook ke automation `Meeting Start → Open Zoom`.

## Prompt

Copy dari `PROMPT-03-email-meeting-zoom-launch.txt`

## Fix penting

Window lookahead harus **≥ interval** (35 menit > 30 menit).  
Jika window hanya 2 menit tapi cek tiap 30 menit → meeting hampir selalu miss.

## Webhook target

Automation: `Meeting Start → Open Zoom`  
ID: `cdac76b4-8cc0-11f1-a7d1-d6b4613131ce`
