# (Special request routes moved below all imports and app initialization)
# app.py

from flask import Flask, render_template, request, redirect, url_for, session, flash
from db_config import get_db_connection
from datetime import datetime
import logging
import psycopg2
import psycopg2.extras
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps


app = Flask(__name__)
app.secret_key = 'sb_secret_-Z49MFbzUmQxBvDLb7Q2dw_c0AHvNuO'

logging.basicConfig(level=logging.INFO)


# ---------------- AUTH HELPERS ----------------
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if role and session.get('user_role') != role:
                flash('Unauthorized access', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_pw = generate_password_hash(password)
        try:
            db = get_db_connection()
            cursor = db.cursor()
            # Only allow first user to be admin, others are users
            cursor.execute('SELECT COUNT(*) FROM users')
            user_count = cursor.fetchone()[0]
            role = 'admin' if user_count == 0 else 'user'
            cursor.execute('INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)',
                           (name, email, hashed_pw, role))
            db.commit()
            cursor.close()
            db.close()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            logging.error(f"Register error: {e}")
            flash('Registration failed. Email may already be used.', 'danger')
            return render_template('register.html')
    return render_template('register.html')

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            db = get_db_connection()
            cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cursor.fetchone()
            cursor.close()
            db.close()
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_role'] = user['role']
                flash('Login successful!', 'success')
                if user['role'] == 'admin':
                    return redirect(url_for('admin'))
                else:
                    return redirect(url_for('index'))
            else:
                flash('Invalid credentials', 'danger')
        except Exception as e:
            logging.error(f"Login error: {e}")
            flash('Login failed.', 'danger')
    return render_template('login.html')

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))
@app.route('/')
def index():
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM books ORDER BY id')
        books = cursor.fetchall()   # ✅ DictRow list
        cursor.close()
        db.close()
        return render_template('index.html', books=books)
    except Exception as e:
        logging.error(f"Index error: {e}")
        return f"ERROR: {e}", 500


# ---------------- SEARCH ----------------
@app.route('/search')
def search():
    query = request.args.get('q', '')
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute(
            'SELECT * FROM books WHERE title ILIKE %s OR author ILIKE %s',
            (f'%{query}%', f'%{query}%')
        )
        books = cursor.fetchall()
        cursor.close()
        db.close()
        return render_template('index.html', books=books, search=query)
    except Exception as e:
        logging.error(f"Search error: {e}")
        return f"ERROR: {e}", 500


# ---------------- BOOK DETAILS ----------------
@app.route('/book/<int:book_id>')
def book_details(book_id):
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM books WHERE id = %s', (book_id,))
        book = cursor.fetchone()
        cursor.close()
        db.close()

        if not book:
            flash('Book not found', 'danger')
            return redirect(url_for('index'))

        return render_template('book_details.html', book=book)
    except Exception as e:
        logging.error(f"Book details error: {e}")
        return f"ERROR: {e}", 500


# ---------------- CART ----------------
@app.route('/add_to_cart/<int:book_id>')
def add_to_cart(book_id):
    cart = session.get('cart', {})
    cart[str(book_id)] = cart.get(str(book_id), 0) + 1
    session['cart'] = cart
    flash('Book added to cart!', 'success')
    return redirect(url_for('index'))


@app.route('/cart')

def cart():
    # Always ensure cart is a dict in session
    if 'cart' not in session or not isinstance(session['cart'], dict):
        session['cart'] = {}
    cart = session['cart']
    books = []
    total = 0

    if not cart:
        return render_template('cart.html', books=[], total=0)

    try:
        db = get_db_connection()
        cursor = db.cursor()
        for book_id, qty in cart.items():
            cursor.execute('SELECT * FROM books WHERE id = %s', (book_id,))
            row = cursor.fetchone()
            if row:
                # Convert to dict if not already
                book = dict(row) if not isinstance(row, dict) else row
                book['quantity'] = qty
                book['subtotal'] = float(book['price']) * qty
                total += book['subtotal']
                books.append(book)
        cursor.close()
        db.close()
        return render_template('cart.html', books=books, total=total)
    except Exception as e:
        logging.error(f"Cart error: {e}")
        return f"ERROR: {e}", 500


# ---------------- PLACE ORDER ----------------
@app.route('/place_order', methods=['POST'])

def place_order():
    name = request.form.get('name')
    email = request.form.get('email')
    cart = session.get('cart', {})

    if not cart:
        flash('Cart is empty', 'danger')
        return redirect(url_for('cart'))

    try:
        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            'INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id',
            (name, email)
        )
        user_id_row = cursor.fetchone()
        user_id = user_id_row['id'] if isinstance(user_id_row, dict) else user_id_row[0]

        cursor.execute(
            'INSERT INTO orders (user_id, order_date) VALUES (%s, %s) RETURNING id',
            (user_id, datetime.now())
        )
        order_id_row = cursor.fetchone()
        order_id = order_id_row['id'] if isinstance(order_id_row, dict) else order_id_row[0]

        for book_id, qty in cart.items():
            cursor.execute(
                'INSERT INTO order_items (order_id, book_id, quantity) VALUES (%s, %s, %s)',
                (order_id, book_id, qty)
            )
            cursor.execute(
                'UPDATE books SET stock = stock - %s WHERE id = %s',
                (qty, book_id)
            )

        db.commit()
        cursor.close()
        db.close()

        session.pop('cart', None)
        flash('Order placed successfully!', 'success')
        return redirect(url_for('index'))

    except Exception as e:
        logging.error(f"Place order error: {e}")
        if 'db' in locals():
            db.rollback()
            db.close()
        flash('Order failed', 'danger')
        return redirect(url_for('cart'))


# ---------------- ADMIN ----------------
@app.route('/admin')
def admin():
    try:
        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute('SELECT * FROM books')
        books = cursor.fetchall()

        cursor.execute(
            '''
            SELECT orders.id, users.name, orders.order_date
            FROM orders
            JOIN users ON orders.user_id = users.id
            ORDER BY orders.id DESC
            '''
        )
        orders = cursor.fetchall()

        cursor.close()
        db.close()
        return render_template('admin.html', books=books, orders=orders)

    except Exception as e:
        logging.error(f"Admin error: {e}")
        return f"ERROR: {e}", 500


# ---------------- ADMIN CRUD ----------------
@app.route('/admin/add_book', methods=['POST'])
def add_book():
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute(
            'INSERT INTO books (title, author, price, category, stock) VALUES (%s, %s, %s, %s, %s)',
            (
                request.form['title'],
                request.form['author'],
                request.form['price'],
                request.form['category'],
                request.form['stock']
            )
        )
        db.commit()
        cursor.close()
        db.close()
        flash('Book added', 'success')
    except Exception as e:
        logging.error(f"Add book error: {e}")
        db.rollback()
        db.close()
        flash('Add failed', 'danger')

    return redirect(url_for('admin'))


@app.route('/admin/update_book/<int:book_id>', methods=['POST'])
def update_book(book_id):
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute(
            'UPDATE books SET title=%s, author=%s, price=%s, category=%s, stock=%s WHERE id=%s',
            (
                request.form['title'],
                request.form['author'],
                request.form['price'],
                request.form['category'],
                request.form['stock'],
                book_id
            )
        )
        db.commit()
        cursor.close()
        db.close()
        flash('Book updated', 'success')
    except Exception as e:
        logging.error(f"Update error: {e}")
        db.rollback()
        db.close()
        flash('Update failed', 'danger')

    return redirect(url_for('admin'))


@app.route('/admin/delete_book/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute('DELETE FROM books WHERE id=%s', (book_id,))
        db.commit()
        cursor.close()
        db.close()
        flash('Book deleted', 'success')
    except Exception as e:
        logging.error(f"Delete error: {e}")
        db.rollback()
        db.close()
        flash('Delete failed', 'danger')

    return redirect(url_for('admin'))


# ---------------- SPECIAL REQUEST (USER) ----------------
@app.route('/request-book', methods=['GET', 'POST'])
def request_book():
    if 'user_id' not in session:
        flash('Login required to request a book.', 'danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        details = request.form.get('details')
        try:
            db = get_db_connection()
            cursor = db.cursor()
            cursor.execute(
                'INSERT INTO special_requests (user_id, title, author, details) VALUES (%s, %s, %s, %s)',
                (session['user_id'], title, author, details)
            )
            db.commit()
            cursor.close()
            db.close()
            flash('Request submitted!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            logging.error(f"Special request error: {e}")
            flash('Failed to submit request.', 'danger')
    return render_template('request_book.html')

# ---------------- SPECIAL REQUESTS (ADMIN PANEL) ----------------
@app.route('/special-requests')
@login_required(role='admin')
def special_requests():
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute(
            '''SELECT sr.*, u.name as user_name FROM special_requests sr JOIN users u ON sr.user_id = u.id ORDER BY sr.id DESC'''
        )
        requests = cursor.fetchall()
        cursor.close()
        db.close()
        return render_template('special_requests.html', requests=requests)
    except Exception as e:
        logging.error(f"Special requests error: {e}")
        return f"ERROR: {e}", 500

# Approve request: add book to store and mark as approved
@app.route('/special-requests/<int:req_id>/approve', methods=['POST'])
@login_required(role='admin')
def approve_special_request(req_id):
    try:
        db = get_db_connection()
        cursor = db.cursor()
        # Get request details
        cursor.execute('SELECT * FROM special_requests WHERE id = %s', (req_id,))
        req = cursor.fetchone()
        if req and req['status'] == 'pending':
            # Add book to store
            cursor.execute('INSERT INTO books (title, author, category, stock, price) VALUES (%s, %s, %s, %s, %s)',
                (req['title'], req['author'], 'Special Demand', 1, 0))
            # Mark request as approved
            cursor.execute('UPDATE special_requests SET status = %s WHERE id = %s', ('approved', req_id))
            db.commit()
        cursor.close()
        db.close()
        flash('Request approved and book added!', 'success')
    except Exception as e:
        logging.error(f"Approve request error: {e}")
        flash('Failed to approve request.', 'danger')
    return redirect(url_for('special_requests'))

# Decline request
@app.route('/special-requests/<int:req_id>/decline', methods=['POST'])
@login_required(role='admin')
def decline_special_request(req_id):
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute('UPDATE special_requests SET status = %s WHERE id = %s', ('declined', req_id))
        db.commit()
        cursor.close()
        db.close()
        flash('Request declined.', 'info')
    except Exception as e:
        logging.error(f"Decline request error: {e}")
        flash('Failed to decline request.', 'danger')
    return redirect(url_for('special_requests'))


if __name__ == '__main__':
    app.run(debug=True)
