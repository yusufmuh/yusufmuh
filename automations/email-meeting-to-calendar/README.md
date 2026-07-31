# Email Meeting → Google Calendar

Automation khusus akun **yusuf.consultan@gmail.com**.

Membaca email undangan / meeting / interview / jadwal / link Meet-Zoom-dll, lalu membuat atau meng-update acara di Google Calendar.

## Opsi A — Google Apps Script (disarankan, langsung di akun Gmail)

Berjalan native di Google account, tanpa Cursor/Composio.

1. Login ke [script.google.com](https://script.google.com) sebagai `yusuf.consultan@gmail.com`
2. **New project** → hapus kode default → tempel isi `EmailMeetingToCalendar.gs`
3. Simpan project (mis. `Email Meeting to Calendar`)
4. Jalankan fungsi `setup`
5. Izinkan akses Gmail + Calendar saat diminta
6. Trigger otomatis tiap **15 menit** sudah terpasang

Fungsi berguna:

| Fungsi | Kegunaan |
|---|---|
| `setup` | Validasi akun, buat label, pasang trigger, sync pertama |
| `syncMeetingEmailsToCalendar` | Jalankan sync manual |
| `dryRunPreview` | Preview 10 email kandidat tanpa menulis calendar |

Email yang sudah diproses ditandai label Gmail `calendar-synced`.

## Opsi B — Cursor Automation + Composio

1. Authenticate **Composio** MCP di Cursor (Settings → MCP → Connect)
2. Connect **Gmail** + **Google Calendar** untuk `yusuf.consultan@gmail.com`
3. Buka [cursor.com/automations/new](https://cursor.com/automations/new)
4. Paste isi `PROMPT.md` sebagai instructions
5. Trigger: scheduled (mis. setiap 15–30 menit)
6. Tools: enable MCP / Composio
7. Repository: **No repository**
8. Save & activate

## Apa yang dideteksi

- Kata kunci: undangan, invitation, meeting, interview, wawancara, jadwal, schedule, agenda, kalender, RSVP, dll.
- Link: Google Meet, Zoom, Microsoft Teams, Webex, Whereby, Calendly
- Data acara: judul, waktu mulai/selesai, lokasi/link, deskripsi, pengirim, attendees

## Catatan

- Default durasi **60 menit** jika end time tidak ada
- Timezone default: `Asia/Jakarta`
- Event duplikat dicegah (judul mirip + waktu ±15 menit, atau meeting URL sama) → di-update, bukan dibuat ulang
- Email tanpa tanggal/waktu yang jelas **tidak** dibuatkan event (dicatat sebagai clarification)
