# 🛒 Dhami Electronics

![License](https://img.shields.io/badge/license-Proprietary-red)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Flask](https://img.shields.io/badge/Flask-2.x-green)
![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey)

**Dhami Electronics** is a full-featured **e-commerce web application** built with **Flask** and **SQLite**. It allows customers to browse electronics products, add them to cart, checkout securely, and track orders — with a clean, mobile-responsive design and robust admin panel.

## 📖 Project Background

This project was developed as a complete **online electronics store** tailored for the Nepali market (with NPR currency and Nepal Timezone support). It includes modern features like OTP-based email verification, order notifications, shipping calculations, and a powerful admin dashboard.

The goal was to build a production-ready e-commerce platform from scratch while learning Flask best practices, user authentication, email integration, and responsive UI design.

---
⚠️ This project is **NOT open source**.  
All code, designs, emails templates, and assets are fully protected and may not be copied or reused without permission.
---

## 🚀 Features

### Customer Features
- Secure user registration with **OTP email verification**
- Login with username or email
- Browse products with discount display and categories
- Product details with reviews & average rating system
- Add to cart with real-time stock checking
- Shopping cart with quantity update and removal
- Smart shipping calculation (Free above NPR 5000, flat NPR 150 otherwise)
- Checkout with address & phone
- Order history and detailed order view
- Order cancellation (within 1 hour for pending orders)

### Admin Features
- Full admin dashboard
- Add, edit, and delete products (with image upload)
- Manage users and promote to admin
- View all orders with status management (Pending → Processing → Shipped → Delivered → Cancelled)
- Real-time stock deduction on order placement

### Notifications & Emails
- Beautiful mobile-responsive HTML emails
- OTP verification for registration & password reset
- Order confirmation to customer
- New order notification to admin
- Order status update emails
- Order cancellation notifications

### Other Highlights
- Nepal Timezone (NPT) support throughout the app
- Responsive & modern UI (mobile-friendly)
- Flask-Login for authentication
- Flask-Mail with Gmail SMTP
- Secure password hashing
- Input validation and flash messages

---

## 🌐 Live Demo

👉 https://dhamielectronics.pythonanywhere.com/

---

## 🧪 Tech Stack

- **Backend:** Flask (Python)
- **Database:** SQLite (with SQLAlchemy ORM)
- **Frontend:** HTML, CSS, Jinja2 templates, Bootstrap (assumed for responsiveness)
- **Authentication:** Flask-Login + Werkzeug security
- **Email:** Flask-Mail (OTP, order confirmations, admin notifications)
- **File Uploads:** Product images with secure filename handling
- **Timezone:** pytz (Asia/Kathmandu)
- **Deployment Ready:** Easy to deploy on PythonAnywhere, Render, or VPS

---

## 📁 Project Structure

```bash
dhami-electronics/
├── app.py                  
├── static/
│   ├── uploads/          
│   ├── css/
│   └── js/
├── templates/            
│   ├── admin/
│   ├── includes/
│   ├── index.html
│   ├── product_detail.html
│   ├── cart.html
│   ├── checkout.html
│   └── ...
├── ecommerce.db           
├── requirements.txt
├── README.md
└── LICENSE.md
```

---

## 🔐 License (Proprietary — All Rights Reserved)

This project is **100% proprietary**.  

You are **NOT allowed** to:
- Copy this code  
- Modify or reuse any part  
- Redistribute or publish it  
- Use it in personal or commercial projects  
- Reverse-engineer or extract logic  
- Upload it anywhere online  

For special permissions, contact the owner directly.

Full legal text is included in the [LICENSE](LICENSE.md) file.

---

## 🤝 Contributions

External contributions are **not accepted**.  
This project is private and owned solely by the author.

---

## 👨‍💻 Author Information

**Name:** [Dinesh Singh Dhami](https://dineshsinghdhami.com.np)  
**GitHub:** [https://github.com/dineshsinghdhami](https://github.com/dineshsinghdhami)  
**Email:** [dineshdhamidn@gmail.com](mailto:dineshdhamidn@gmail.com)
