# Online Book Store (Flask + MySQL)

Full-stack demo for browsing, ordering, and requesting books. Flask handles the UI + routes, PyMySQL talks to a MySQL database, and Bootstrap keeps the templates simple.

## Features
- Public catalog with search, detail page, and RBAC-protected cart
- Secure registration/login with hashed passwords and role-aware navigation
- Enhanced checkout: cart items track rate/subtotal, Buy page simulates payment, and orders persist with status
- Admin dashboard for CRUD on books plus a dedicated Orders panel with approve/reject actions
- Special request workflow so users can ask admins to stock a title
- Notification system: users are alerted on login when admins approve/reject their rentals

## Prerequisites
- Python 3.10+ with `pip`
- MySQL Server (XAMPP, WampServer, MAMP, Docker, etc.)
- Optional: Git + a virtual environment tool (`venv`/`conda`)

## 1. Clone & Install
```bash
git clone <repo-url>
cd OnlineBookStore
python -m venv venv   # optional but recommended
venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Create the Database + Sample Data
Run the all-in-one script (drops/creates the DB, tables, and seeds demo rows).

### Using MySQL CLI
```bash
mysql -u root -p < database/online_book_store.sql
```

### Using phpMyAdmin
1. Open phpMyAdmin → SQL tab.
2. Paste the contents of `database/online_book_store.sql`.
3. Execute – it will create `online_book_store` with starter data (books, users, orders, special requests).

Seeded credentials:
- Admin: `admin@example.com` / `admin123`
- Users: `ava@example.com`, `leo@example.com` (same password as above)

## 3. Configure Environment Variables
Copy `.env` and tweak credentials if needed (match your MySQL install):
```
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=online_book_store
DB_USER=root
DB_PASSWORD=your_mysql_password
FLASK_SECRET_KEY=replace_with_random_value
```

The Flask app loads this file automatically via `python-dotenv`.

## 4. Run the App
```bash
venv\Scripts\activate   # if you created a venv
python app.py             # or: flask run
```
Browse to [http://127.0.0.1:5000](http://127.0.0.1:5000). Use `/login` to access user features, `/admin` for the dashboard, and `/special-requests` to manage queued requests (admin-only).

### User Flow (Role = user)
1. Login with a seeded user (or register as a new one).
2. Browse books and click **Add to Cart** (only visible for authenticated users).
3. Review the cart to see Book, Quantity, Rate, Subtotal, and Total. Click **Buy** to open the payment scanner tab, then mark the payment as successful to finalize the rental.
4. Track every order from **My Orders**; statuses change to *Approved* or *Rejected* when the admin acts.
5. On every login, you'll get a notification if an order's status changed since your last visit.

### Admin Flow (Role = admin)
1. Login with the seeded admin account.
2. Use the **Admin Panel** link to add/update/delete books.
3. Scroll to the **Orders** section to review usernames, requested books, totals, and pending statuses.
4. Approve or Reject rentals with the dedicated buttons; the system flips the status and notifies the corresponding user on their next login.
5. Use **Special Demand** to review book requests submitted by users.

## 5. Deploying with Apache + mod_wsgi (optional)
1. Install `mod_wsgi` for Apache.
2. Point the WSGI application to `app:app` inside this folder.
3. Ensure the same environment variables are available (system env or `SetEnv`).
4. Install requirements into the environment Apache uses and restart the service.

## Troubleshooting
- **Cannot connect to DB**: verify MySQL is running, credentials in `.env` match, and the user has privileges on `online_book_store`.
- **Missing columns**: re-run `database/online_book_store.sql`; it aligns exactly with the current Flask models.
- **Admin login fails**: make sure the seed data was inserted; delete the DB and re-run the SQL script if needed.
- **Static assets not updating**: clear your browser cache or append `?v=1` to the CSS link while developing.

Happy building! Update templates, add pagination, or hook in a real payment gateway once you grasp the basics.
