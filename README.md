# College Library Management Portal – SUPER5

A Flask + MySQL library website with responsive mobile UI and PWA support.

## Run on Windows

```powershell
cd C:\Users\SONAM\OneDrive\Desktop\python\CollegeLibrary_Web_SUPER5
py -m pip install -r requirements.txt
py app.py
```

Open:

- Laptop: http://127.0.0.1:5000
- Same Wi-Fi phone: http://<LAPTOP-IP>:5000

## Demo logins

- admin / admin123
- librarian / lib123
- staff / staff123
- student / student123
- faculty / faculty123

## PWA / Android

The project includes `manifest.json`, `sw.js`, install UI, and responsive layouts. For Android Chrome **Install app / Add to Home screen** works reliably after the site is deployed on an HTTPS domain. A local IP over plain HTTP can be used for testing, but browser install/service-worker support may be restricted.

## New SUPER5 modules

Study seats, study rooms, library entry/exit, book donations, inter-library loans, help desk, book requests/voting, fine disputes, library events, book clubs, reading plans, similar books, data quality, activity heatmap, security audit, reading certificates, rule-based library assistant, public landing page, PWA install support.
