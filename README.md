# Personal Future Dashboard

Static dashboard JSON + a local desktop editor.

## What ships to static hosting

Only the `public/` folder needs to be deployed (GitHub Pages, Netlify, etc.).

## Local editing workflow

1. Run the local editor server:
   - `python local_server.py`
2. Open the editor:
   - `http://localhost:8787/editor`
3. Preview the dashboard:
   - `http://localhost:8787/dashboard`
4. Publish:
   - Commit/push the `public/` folder to your static host.

## Data files

- `data/left_column.json`
- `data/big_events.json`
- `data/right_column.json`

All updates regenerate `public/dashboard.json`.

## Static dashboard

Open `public/index.html` anywhere that can serve static files.
