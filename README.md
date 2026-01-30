# Online Book Store (Flask + MySQL)

A simple, beginner-friendly Online Book Store web app using Python, Flask, and MySQL. Suitable for college/diploma final-year projects.

## Features
- Home page: List all books
- Search books by title or author
- Book details page
- Add to cart (session-based)
- Place order (no payment gateway)
- Admin panel: Add, update, delete books; view orders

## Tech Stack
- Python 3
- Flask
- MySQL (mysql-connector-python)
- HTML, CSS, Bootstrap (CDN)

## Project Structure
```
OnlineBookStore/
│── app.py
│── db_config.py
│── requirements.txt
│── database/
│   └── online_book_store.sql
│── templates/
│   ├── base.html
│   ├── index.html
│   ├── book_details.html
│   ├── cart.html
│   ├── admin.html
│── static/
│   └── css/style.css
│── README.md
```

## Database Setup
1. Install MySQL and start the MySQL server.
2. Open MySQL command line or a tool like phpMyAdmin.
3. Run the SQL script in `database/online_book_store.sql` to create the database and tables:
   ```sql
   SOURCE path/to/OnlineBookStore/database/online_book_store.sql;
   ```

## Configuration
- Edit `db_config.py` if your MySQL username/password is different.
- Default: user=`root`, password=``, database=`online_book_store`

## Install Dependencies
Open terminal in the `OnlineBookStore` folder and run:
```bash
pip install -r requirements.txt
```

## Run the Project
```bash
python app.py
```
- Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

## Usage
- Browse books, search, view details, add to cart, and place orders.
- Admin panel: `/admin` (no login, for demo simplicity)

## Notes
- No payment gateway or advanced authentication (for simplicity).
- For demo/testing, you can add books via the admin panel.

## For Submission
- Include all files and folders as shown above.
- Attach screenshots of working app if required by your college.

---
**Project by: [Your Name]**
