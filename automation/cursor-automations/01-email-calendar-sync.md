# Automation 1: Email → Calendar Sync (Setiap 12 Jam)

**Name:** `Email Meeting Sync → Calendar`  
**Trigger:** Scheduled — `0 */12 * * *` (setiap 12 jam)  
**Repository:** No repository  
**Tools:** MCP server, Memories

---

## Tujuan

Scan seluruh akun Gmail, deteksi undangan meeting/interview/jadwal, buat event di Google Calendar `yusuf.consultan@gmail.com`.

## Akun

1. yusuf.consultan@gmail.com (primary)
2. muhammad.yusuf010@binus.ac.id
3. kuron.kursusonline@gmail.com
4. muhammad.yusufbinbambang@gmail.com
5. myustadzbambang@gmail.com
6. yuukina99@gmail.com
7. muhammad.yusuf010@edukator.elevaite.id

## Prompt

Copy dari `PROMPT-01-email-sync.txt`

## Catatan

- Query Gmail pakai `newer_than:2d` agar aman antar run 12 jam
- Dedup via Memories
- Timezone: Asia/Jakarta
