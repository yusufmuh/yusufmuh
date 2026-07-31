# Automation 1: Email → Calendar Sync (Scheduled)

**Trigger:** Scheduled — every 1 hour (`0 * * * *`)
**Repository:** No repository
**Tools:** MCP server (meeting-automation), Memories

---

## Tujuan

Scan seluruh akun Gmail yang dikonfigurasi, deteksi email undangan meeting/interview/jadwal, lalu buat event di Google Calendar utama (yusuf.consultan@gmail.com).

## Akun Gmail yang Dimonitor

1. yusuf.consultan@gmail.com (primary)
2. muhammad.yusuf010@binus.ac.id
3. kuron.kursusonline@gmail.com
4. muhammad.yusufbinbambang@gmail.com
5. myustadzbambang@gmail.com
6. yuukina99@gmail.com
7. muhammad.yusuf010@edukator.elevaite.id

## Langkah Eksekusi

1. Panggil tool MCP `sync_emails_to_calendar` untuk scan semua akun dan sync ke calendar.
2. Jika sync gagal, gunakan `gmail_search` per akun dengan query:
   ```
   in:inbox (subject:(undangan OR invitation OR invite OR meeting OR interview OR wawancara OR jadwal OR zoom OR webinar) OR "zoom.us" OR "meet.google.com" OR has:attachment filename:ics) newer_than:1d
   ```
3. Untuk setiap email yang belum diproses (cek memories), panggil `gmail_read_meeting` lalu `calendar_create_event` jika confidence >= 0.5.
4. Simpan message ID yang sudah diproses ke memories agar tidak duplikat.

## Aturan Parsing

- Jika email punya attachment .ics → parse dan buat event langsung
- Jika ada link Zoom/Meet/Teams → simpan di field location calendar
- Jika waktu tidak jelas → jangan buat event, log untuk review manual
- Timezone: Asia/Jakarta (WIB)

## Output

Buat ringkasan:
- Berapa akun di-scan
- Berapa meeting ditemukan
- Berapa event dibuat di calendar
- Daftar event baru (judul, waktu, link meeting)
- Error per akun jika ada
