# Hotel Management System

A full-featured, lightweight **Hotel Management and Billing System** designed with Python, Flask, and MySQL. It features a beautifully simple dark-themed user interface, comprehensive database constraints for reliability, and a clean, maintainable codebase ready for localized deployment or production release using platforms like Vercel.

---

##  Features
- **Live Room Bookings:** View available rooms dynamically, set check-in/check-out dates, and secure a reservation directly mapping to registered customers.
- **Customer Management System:** Complete, persistent records of every customer who has stayed in the hotel. Track previous customers and current customers efficiently.
- **Robust Billing & Payments:** An integrated checkout portal that automatically generates invoices based on room stay duration. Payments map directly to reservations avoiding data cascades, maintaining full historical billing records.
- **CSV Exports:** Admins can export all active and historical customer records immediately to `.csv` data dumps.
- **Minimal Server Dependencies:** Fast, light-weight back-end. Uses `PyMySQL` allowing serverless functionality without heavy system-level drivers.

##  Tech Stack
- **Backend**: Python 3.x, Flask
- **Database**: MySQL 8.x, PyMySQL, cryptography
- **Frontend**: HTML5, Vanilla CSS3 (Custom Dark/Glassmorphic aesthetics), Jinja2 Templating

## Database Architecture
The system relies on five tightly-coupled relational tables:
1. **`Customer`**: Core customer information (Name, Contact, Address, ID Proof).
2. **`Room`**: Hotel inventory details (Room No, Type, Price, Availability Status).
3. **`Reservation`**: Logs the linking of Customers to Rooms, storing active dates.
4. **`Bill`**: Generates upon checkout relative to the `Reservation`.
5. **`Payment`**: Records individual financial transactions corresponding to generated `Bill`s.

---

##  Getting Started

### 1. Prerequisites
Make sure to have the following installed locally on your system:
- **Python 3.8+**
- **MySQL Server** (running locally or on a cloud provider like PlanetScale)

### 2. Clone and Install Dependencies
Create a virtual environment to isolate the project requirements, and install packages.

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Database Configuration
By default, the application will look for `.env` variables or fallback to defaults in `config.py`. Update these to reflect your local connection strings.

Inside `config.py`:
```python
MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "your_password_here")
MYSQL_DB = os.environ.get("MYSQL_DB", "hotel_db")
```

### 4. Running the Server
Start the Flask development server seamlessly!
```bash
flask run
# or
python app.py
```
Navigate to `http://127.0.0.1:5000` in your web browser!

## 📖 Application Flow Workflow
1. **Home / Dashboard**: View navigation layout.
2. **Make a Reservation**: Choose dates -> See available rooms -> Book.
3. **Active Reservations**: View guests currently checked in.
4. **Checkout**: Enter reservation ID, view the bill overview, finalize checkout, and make payments. The detailed bill logs securely into your history panel below the checkout module.
5. **Customer Details**: Filter customers depending on live reservations or previous history.

---

*Designed for efficient workflows and aesthetic presentation.*
