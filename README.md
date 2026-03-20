# Hotel Management System (DBMS Project)

Flask-based hotel reservation & billing demo app — suitable for demo or classroom presentation.

Quick start (presentation-ready)

1. Create and activate a Python virtual environment, then install dependencies:

Windows PowerShell:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Configure the database connection in `config.py` (MySQL credentials). The app assumes tables: `Customer`, `Room`, `Reservation`, `Bill`, and `Payment`.

3. Run the server:

```powershell
setx SECRET_KEY "your-secret"
flask run
```

Presentation notes

- The repository excludes the local virtual environment and logs via `.gitignore`.
- Temporary test scripts have been removed to keep the repo tidy; you can manually exercise flows through the UI.
- To demonstrate: create a customer, make a reservation, perform checkout to generate a bill, then mark the bill paid.

Important files

- `app.py` — main Flask app and routes
- `templates/` — Jinja2 templates for UI
- `Static/style.css` — custom styling and hero image
- `config.py` — database credentials (not checked in with sensitive values)
- `requirements.txt` — Python dependencies

Routes (demo)

- `/` Home
- `/reservation_start` Make a reservation (customer form)
- `/available_rooms` List available rooms for chosen dates
- `/room/<room_no>` View room and reserve
- `/reservations` Active reservations
- `/checkout` Admin checkout / bill generation
- `/customers` Split view: current customers (with active reservations) and previous customers

If you want, I can also:

- Run a quick smoke test of the checkout/payment flow (needs a running MySQL instance with the expected schema).
- Create a small SQL file with the expected table definitions for easier demo setup.
