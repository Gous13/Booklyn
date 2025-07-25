# Booklyn

A simple Library Management System built with Flask and SQLite, designed to help Admins manage books and users, while allowing Users to issue, request, and track books.

## 🚀 Features

### ✅ User Features
- Sign up & Login
- View available books
- Request and issue books
- View issued books with due date & fines

### ✅ Admin Features
- Login as Admin
- Manage books (add, edit, delete)
- Manage members
- Track transactions and fines

## 🛠 Tech Stack
- **Backend:** Flask, Jinja2
- **Frontend:** HTML, CSS, Bootstrap
- **Database:** SQLite
- **Deployment:** Render

## 📂 Project Structure
```
Library Management System
├── app.py
├── requirements.txt
├── Procfile
├── runtime.txt
├── templates/
│   ├── base.html
│   ├── user/
│   └── admin/
└── static/
    ├── css/
    └── js/
```

## ⚡ Installation & Run Locally

1. **Clone the repo**
    ```bash
    git clone https://github.com/Gous13/Booklyn.git
    cd Booklyn
    ```

2. **Create a virtual environment & install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3. **Run the Flask app**
    ```bash
    python app.py
    ```

4. **Open in browser**
    ```
    http://127.0.0.1:5000
    ```

---
Enjoy managing your library! 📖
