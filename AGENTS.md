# AGENTS.md

## Cursor Cloud specific instructions

### What this repo is
This is a static front-end learning project (HTML/CSS/JavaScript exercises, in Indonesian — "latihan" = exercise). Bootstrap 5 is **vendored** in `HTML awal/latihan 1/bootstrap/`, so there are **no packages to install**, no build step, and no automated test/lint tooling. There is no `package.json`, `Makefile`, or CI.

Notable pages (under `HTML awal/latihan 1/`):
- `medicalclinic.html` — has interactive JavaScript (`script.js`): a "Book an Appointment" button and a contact form that show `alert()` dialogs. Best page for an interactive end-to-end smoke test.
- `latihan1.html` — the default preview page referenced by the original author's VS Code `livePreview` setting.
- `latihanbootstrap5.html`, `WebsitePinjol.html`, `tabel.html`, etc. — Bootstrap/HTML exercises.

### Running it (dev)
There is no dev server framework. The intended workflow (per `.vscode/settings.json`) is VS Code Live Preview, i.e. any static HTTP server. Serve the repo root so directory/relative asset paths resolve:

```
python3 -m http.server 8000
```

Then open pages by URL, e.g. `http://localhost:8000/HTML%20awal/latihan%201/medicalclinic.html`.

### Gotchas
- Directory and file names contain **spaces** (`HTML awal`, `latihan 1`, `Css Awal`). URL-encode spaces as `%20` when constructing URLs, and quote paths in the shell.
- `medicalclinic.html` renders a block of raw CSS/HTML as plain text below the form. This is a **pre-existing content bug** in the file (styles/markup placed after the closing `</html>` tag), not an environment problem. The interactive JS still works.
- `tokoonlinechatgpbt.html` is empty (0 bytes).

### Lint / test / build
None exist in this repo. Nothing to run.
