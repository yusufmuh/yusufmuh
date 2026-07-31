# Letakkan file OAuth di sini

## credentials.json

Download dari [Google Cloud Console](https://console.cloud.google.com/apis/credentials):

1. Buat project baru (atau gunakan yang ada)
2. Enable **Gmail API** dan **Google Calendar API**
3. OAuth consent screen → External → **Publish** (penting agar token tidak expire 7 hari)
4. Credentials → Create OAuth Client ID → **Desktop app**
5. Download JSON → simpan sebagai `credentials.json` di folder ini

## tokens/

Folder ini otomatis dibuat saat Anda menjalankan `python scripts/connect_account.py`.
Setiap akun Gmail akan punya file token sendiri (OAuth, bukan password).

**JANGAN commit folder ini ke git.**
