from flask import Flask, render_template, request, redirect, url_for, Response

try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass

from flask_mysqldb import MySQL
from datetime import date
import re
import csv
import io
import config
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

# load DB config and init MySQL
app.config['MYSQL_HOST'] = config.MYSQL_HOST
app.config['MYSQL_USER'] = config.MYSQL_USER
app.config['MYSQL_PASSWORD'] = config.MYSQL_PASSWORD
app.config['MYSQL_DB'] = config.MYSQL_DB
mysql = MySQL(app)

def _log_exception(e):
    import traceback
    tb = traceback.format_exc()
    try:
        with open('error.log', 'a', encoding='utf-8') as f:
            f.write(tb + '\n')
    except Exception:
        pass


@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return e
    _log_exception(e)
    return "Internal server error", 500


@app.route('/')
def home():
    return render_template('index.html')


# Minimal reservation start route (keeps original template behavior)
@app.route('/reservation_start', methods=['GET', 'POST'])
def reservation_start():
    today = date.today().isoformat()
    if request.method == 'POST':
        check_in = request.form.get('check_in')
        check_out = request.form.get('check_out')
        
        try:
            in_date = date.fromisoformat(check_in)
            out_date = date.fromisoformat(check_out)
            if in_date < date.today():
                return "Check-in date cannot be in the past", 400
            if in_date >= out_date:
                return "Invalid dates: check-out must be after check-in", 400
        except Exception:
            return "Invalid date format", 400

        try:
            cur = mysql.connection.cursor()
            # Find rooms that do not have overlapping reservations for the requested dates
            cur.execute('''
                SELECT * FROM Room 
                WHERE room_no NOT IN (
                    SELECT room_no FROM Reservation 
                    WHERE check_out_date > %s AND check_in_date < %s
                )
            ''', (check_in, check_out))
            rooms = cur.fetchall()
            cur.close()
        except Exception as e:
            _log_exception(e)
            rooms = []
        return render_template('available_rooms.html', rooms=rooms, form_data=request.form)
    return render_template('reservation_start.html', today=today)


# VIEW RESERVATIONS
@app.route("/reservations")
def reservations():

    cur = mysql.connection.cursor()

    cur.execute("""
    SELECT r.reservation_id, c.customer_id, c.first_name, c.last_name, r.room_no,
    r.check_in_date, r.check_out_date
    FROM Reservation r
    JOIN Customer c ON r.customer_id=c.customer_id
    WHERE r.reservation_id NOT IN (SELECT b.reservation_id FROM Bill b JOIN Payment p ON b.bill_id = p.bill_id)
    """)

    data = cur.fetchall()

    return render_template("reservations_list.html",data=data)


@app.route('/customers')
def customers_list():
    cur = None
    try:
        cur = mysql.connection.cursor()
        # customers with active reservations
        cur.execute('''
            SELECT c.customer_id, c.first_name, c.last_name, c.street, c.city, c.pin, c.email, c.phone
            FROM Customer c
            WHERE EXISTS (
                SELECT 1 FROM Reservation r 
                WHERE r.customer_id = c.customer_id 
                AND r.reservation_id NOT IN (SELECT b.reservation_id FROM Bill b JOIN Payment p ON b.bill_id = p.bill_id)
            )
            ORDER BY c.customer_id DESC
        ''')
        current_customers = cur.fetchall()

        # customers with no active reservations (previous customers)
        cur.execute('''
            SELECT c.customer_id, c.first_name, c.last_name, c.street, c.city, c.pin, c.email, c.phone
            FROM Customer c
            WHERE NOT EXISTS (
                SELECT 1 FROM Reservation r 
                WHERE r.customer_id = c.customer_id
                AND r.reservation_id NOT IN (SELECT b.reservation_id FROM Bill b JOIN Payment p ON b.bill_id = p.bill_id)
            ) AND EXISTS (
                SELECT 1 FROM Reservation r WHERE r.customer_id = c.customer_id
            )
            ORDER BY c.customer_id DESC
        ''')
        previous_customers = cur.fetchall()

        return render_template('customers_list.html', current_customers=current_customers, previous_customers=previous_customers)
    except Exception as e:
        # return empty lists and show error in template if needed
        return render_template('customers_list.html', current_customers=[], previous_customers=[], error=str(e))
    finally:
        if cur:
            try:
                cur.close()
            except Exception:
                pass


# Edit customer
@app.route('/customer/<int:customer_id>/edit', methods=['GET','POST'])
def edit_customer(customer_id):
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        form = request.form
        cur.execute('''
            UPDATE Customer SET first_name=%s, last_name=%s, street=%s, city=%s, pin=%s, email=%s, phone=%s, id_proof_type=%s, id_proof_number=%s
            WHERE customer_id=%s
        ''', (
            form.get('first_name'), form.get('last_name'), form.get('street'), form.get('city'), form.get('pin'),
            form.get('email'), form.get('phone'), form.get('id_proof_type'), form.get('id_proof_number'), customer_id
        ))
        mysql.connection.commit()
        return redirect(url_for('customer_detail', customer_id=customer_id))

    cur.execute('SELECT customer_id, first_name, last_name, street, city, pin, email, phone, id_proof_type, id_proof_number FROM Customer WHERE customer_id=%s', (customer_id,))
    customer = cur.fetchone()
    return render_template('customer_edit.html', customer=customer)


# Delete customer (POST)
@app.route('/customer/<int:customer_id>/delete', methods=['POST'])
def delete_customer(customer_id):
    cur = mysql.connection.cursor()
    # remove reservations first to avoid FK constraints
    try:
        cur.execute('DELETE FROM Reservation WHERE customer_id=%s', (customer_id,))
        cur.execute('DELETE FROM Customer WHERE customer_id=%s', (customer_id,))
        mysql.connection.commit()
    except Exception:
        mysql.connection.rollback()
    return redirect(url_for('customers_list'))


@app.route('/customers/export')
def export_customers():
    cur = mysql.connection.cursor()
    cur.execute('SELECT customer_id, first_name, last_name, street, city, pin, email, phone, id_proof_type, id_proof_number FROM Customer')
    rows = cur.fetchall()
    cur.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['customer_id','first_name','last_name','street','city','pin','email','phone','id_proof_type','id_proof_number'])
    for r in rows:
        writer.writerow(r)

    resp = Response(output.getvalue(), mimetype='text/csv')
    resp.headers['Content-Disposition'] = 'attachment; filename=customers.csv'
    return resp


@app.route('/room/<room_no>', methods=['GET','POST'])
def room_detail(room_no):
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        form = request.form
        # either existing customer_id or create new customer
        customer_id = form.get('customer_id')
        check_in = form.get('check_in')
        check_out = form.get('check_out')

        # validate dates
        try:
            in_date = date.fromisoformat(check_in)
            out_date = date.fromisoformat(check_out)
            if in_date < date.today():
                return "Check-in date cannot be in the past", 400
            if in_date >= out_date:
                return "Invalid dates: check-out must be after check-in", 400
        except Exception:
            return "Invalid date format", 400

        # re-check availability
        cur.execute('''
            SELECT COUNT(*) FROM Reservation
            WHERE room_no=%s AND NOT (check_out_date <= %s OR check_in_date >= %s)
        ''', (room_no, check_in, check_out))
        conflict = cur.fetchone()[0]
        if conflict > 0:
            return "Room not available for selected dates", 400

        if not customer_id:
            # friendly handling: if email exists reuse customer, otherwise create
            email = form.get('email')
            if email:
                cur.execute('SELECT customer_id FROM Customer WHERE email=%s', (email,))
                found = cur.fetchone()
                if found:
                    customer_id = found[0]
            if not customer_id:
                cur.execute('''
                    INSERT INTO Customer (first_name,last_name,street,city,pin,email,phone,id_proof_type,id_proof_number)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ''', (
                    form.get('first_name'), form.get('last_name'), form.get('street'), form.get('city'),
                    form.get('pin'), form.get('email'), form.get('phone'), form.get('id_proof_type'), form.get('id_proof_number')
                ))
                mysql.connection.commit()
                customer_id = cur.lastrowid

        # create reservation
        cur.execute('''
            INSERT INTO Reservation (customer_id, room_no, check_in_date, check_out_date)
            VALUES (%s,%s,%s,%s)
        ''', (customer_id, room_no, check_in, check_out))
        mysql.connection.commit()
        reservation_id = cur.lastrowid
        cur.execute('UPDATE Room SET status=%s WHERE room_no=%s', ('Booked', room_no))
        mysql.connection.commit()
        return render_template('reservation_success.html', reservation_id=reservation_id)

    # GET
    # get room details
    cur.execute('SELECT room_no, room_type, price, status FROM Room WHERE room_no=%s', (room_no,))
    row = cur.fetchone()
    if not row:
        return redirect(url_for('reservations'))
    room = {'room_no': row[0], 'room_type': row[1], 'price': row[2], 'status': row[3]}

    # optional prefill customer
    customer = None
    customer_id = request.args.get('customer_id')
    if customer_id:
        cur.execute('SELECT customer_id, first_name, last_name FROM Customer WHERE customer_id=%s', (customer_id,))
        customer = cur.fetchone()

    check_in = request.args.get('check_in', '')
    check_out = request.args.get('check_out', '')

    return render_template('room_detail.html', room=room, customer=customer, check_in=check_in, check_out=check_out)


# CUSTOMER DETAIL
@app.route('/customer/<int:customer_id>')
def customer_detail(customer_id):
    cur = mysql.connection.cursor()
    cur.execute('''
        SELECT customer_id, first_name, last_name, street, city, pin, email, phone, id_proof_type, id_proof_number
        FROM Customer WHERE customer_id = %s
    ''', (customer_id,))
    customer = cur.fetchone()

    cur.execute('''
        SELECT reservation_id, room_no, check_in_date, check_out_date
        FROM Reservation WHERE customer_id = %s
        ORDER BY check_in_date DESC
    ''', (customer_id,))
    reservations = cur.fetchall()

    return render_template('customer_detail.html', customer=customer, reservations=reservations)


# RESERVATION DETAIL
@app.route('/reservation/<int:reservation_id>')
def reservation_detail(reservation_id):
    cur = mysql.connection.cursor()
    cur.execute('''
        SELECT r.reservation_id, r.room_no, r.check_in_date, r.check_out_date,
               c.customer_id, c.first_name, c.last_name, c.email, c.phone
        FROM Reservation r
        JOIN Customer c ON r.customer_id = c.customer_id
        WHERE r.reservation_id = %s
    ''', (reservation_id,))
    row = cur.fetchone()
    if not row:
        return redirect('/reservations')

    reservation = {
        'reservation_id': row[0], 'room_no': row[1], 'check_in': row[2], 'check_out': row[3]
    }
    customer = {
        'customer_id': row[4], 'first_name': row[5], 'last_name': row[6], 'email': row[7], 'phone': row[8]
    }
    return render_template('reservation_detail.html', reservation=reservation, customer=customer)


# Known amenity definitions (name + cost) — must match checkout.html values
AMENITY_MAP = {
    'breakfast':       {'name': 'Breakfast',        'cost': 350},
    'airport_transfer':{'name': 'Airport Transfer', 'cost': 800},
    'spa':             {'name': 'Spa & Wellness',   'cost': 1200},
    'laundry':         {'name': 'Laundry Service',  'cost': 250},
    'gym':             {'name': 'Gym Access',       'cost': 300},
    'minibar':         {'name': 'Mini Bar',         'cost': 500},
    'room_service':    {'name': 'Room Service',     'cost': 400},
    'swimming_pool':   {'name': 'Swimming Pool',    'cost': 600},
}

GST_RATE = 0.12  # 12% GST (CGST 6% + SGST 6%)

# CHECKOUT
@app.route("/checkout", methods=["GET","POST"])
def checkout():

    if request.method == "POST":

        reservation_id_raw = (request.form.get("reservation_id") or "").strip()
        # allow IDs like "R123" or "123" — extract digits
        m = re.search(r"\d+", reservation_id_raw)
        if not m:
            return "Invalid reservation id", 400
        reservation_id = m.group(0)
        actual_check_out = request.form.get("actual_check_out", "")

        cur = mysql.connection.cursor()

        cur.execute("""
        SELECT c.first_name,c.last_name,r.room_no,r.check_in_date,
        r.check_out_date,rm.price
        FROM Reservation r
        JOIN Customer c ON r.customer_id=c.customer_id
        JOIN Room rm ON r.room_no=rm.room_no
        WHERE r.reservation_id=%s
        """,(reservation_id,))

        row = cur.fetchone()
        if not row:
            return "Reservation not found", 404

        cust_first, cust_last, room_no, check_in_date, stored_check_out, price = row

        # determine actual checkout date (admin can override)
        if actual_check_out:
            try:
                actual_out_date = date.fromisoformat(actual_check_out)
            except Exception:
                return "Invalid actual check-out date format", 400
            # update reservation to reflect true checkout
            try:
                cur.execute('UPDATE Reservation SET check_out_date=%s WHERE reservation_id=%s', (actual_check_out, reservation_id))
                mysql.connection.commit()
            except Exception:
                mysql.connection.rollback()
            out_date = actual_out_date
        else:
            out_date = stored_check_out

        days = (out_date - check_in_date).days
        if days < 0:
            days = 0
        room_total = days * price

        # --- Amenities ---
        selected_amenity_keys = request.form.getlist('amenity')
        amenities = []
        amenity_total = 0
        for key in selected_amenity_keys:
            if key in AMENITY_MAP:
                info = AMENITY_MAP[key]
                amenities.append({'name': info['name'], 'cost': info['cost']})
                amenity_total += info['cost']

        # --- GST Calculation ---
        subtotal = room_total + amenity_total
        gst_total = round(subtotal * GST_RATE, 2)
        cgst = round(subtotal * GST_RATE / 2, 2)
        sgst = round(subtotal * GST_RATE / 2, 2)
        total = round(subtotal + gst_total, 2)

        try:
            cur.execute("""
            INSERT INTO Bill(reservation_id,payment_date,total_amount)
            VALUES(%s,CURDATE(),%s)
            """,(reservation_id, total))
            mysql.connection.commit()
            bill_id = cur.lastrowid
        except Exception as e:
            # If a bill already exists for this reservation, fetch it and show existing bill
            err = str(e)
            if 'Duplicate entry' in err and 'reservation_id' in err:
                try:
                    cur.execute('SELECT bill_id, total_amount, payment_date FROM Bill WHERE reservation_id=%s', (reservation_id,))
                    existing = cur.fetchone()
                    if existing:
                        bill_id = existing[0]
                        total = existing[1]
                    else:
                        raise
                except Exception:
                    raise
            else:
                raise

        data = (cust_first, cust_last, room_no, check_in_date, out_date, price)

        return render_template("bill.html",
                       data=data,
                       days=days,
                       room_total=room_total,
                       amenities=amenities,
                       amenity_total=amenity_total,
                       subtotal=subtotal,
                       cgst=cgst,
                       sgst=sgst,
                       gst_total=gst_total,
                       total=total,
                       bill_id=bill_id,
                       reservation_id=reservation_id)

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT b.bill_id, b.reservation_id, c.first_name, c.last_name, 
               b.payment_date, b.total_amount, p.amount, p.payment_mode, c.customer_id
        FROM Bill b
        JOIN Payment p ON b.bill_id = p.bill_id
        JOIN Reservation r ON b.reservation_id = r.reservation_id
        JOIN Customer c ON r.customer_id = c.customer_id
        ORDER BY b.bill_id DESC
    """)
    history = cur.fetchall()
    return render_template("checkout.html", history=history)


# PAYMENT
@app.route("/payment", methods=["POST"])
def payment():

    bill_id = request.form["bill_id"]
    amount = request.form["amount"]
    mode = request.form["mode"]

    cur = mysql.connection.cursor()
    if not bill_id:
        return "Bill id missing", 400

    # ensure bill exists before inserting payment to satisfy FK constraint
    cur.execute('SELECT reservation_id FROM Bill WHERE bill_id=%s', (bill_id,))
    bill_row = cur.fetchone()
    if not bill_row:
        return "Bill not found", 400

    # insert payment
    try:
        cur.execute("""
        INSERT INTO Payment(bill_id,amount,payment_mode)
        VALUES(%s,%s,%s)
        """,(bill_id,amount,mode))
        mysql.connection.commit()
    except Exception:
        mysql.connection.rollback()
        return "Failed to record payment", 500

    # After payment, remove reservation and free the room
    try:
        res_id = bill_row[0]
        if res_id:
            # get room_no before deleting reservation
            cur.execute('SELECT room_no FROM Reservation WHERE reservation_id=%s', (res_id,))
            r = cur.fetchone()
            room_no = r[0] if r else None

            # No longer deleting the reservation to preserve bill and payment history.

            # mark room available
            if room_no:
                try:
                    cur.execute('UPDATE Room SET status=%s WHERE room_no=%s', ('Available', room_no))
                    mysql.connection.commit()
                except Exception:
                    mysql.connection.rollback()
    except Exception:
        mysql.connection.rollback()

    # show a simple confirmation page instead of redirect
    return render_template('payment_success.html')


if __name__ == "__main__":
    app.run(debug=True)