from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
import os
from datetime import datetime
import random
import re
import pytz 
from pytz import timezone

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email Configuration for OTP and Notifications
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'noreply.dhamielectronics@gmail.com'
app.config['MAIL_PASSWORD'] = 'ziwp apvc oals iwme'
app.config['MAIL_DEFAULT_SENDER'] = 'noreply.dhamielectronics@gmail.com'

# Admin email address for order notifications
ADMIN_EMAIL = 'noreply.dhamielectronics@gmail.com'

# Upload folder for product images
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Create upload folder if not exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Shipping Settings
FREE_SHIPPING_THRESHOLD = 5000  # Free shipping for orders above NPR 5000
BASE_SHIPPING_FEE = 150  # Minimum shipping fee for orders under NPR 5000

def calculate_shipping(subtotal):
    """Calculate shipping fee based on subtotal"""
    # Free shipping for orders above NPR 5000
    if subtotal >= FREE_SHIPPING_THRESHOLD:
        return 0
    
    # Flat shipping fee of NPR 150 for orders under NPR 5000
    return BASE_SHIPPING_FEE

mail = Mail(app)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# Nepali Timezone Helper Functions
NEPAL_TZ = timezone('Asia/Kathmandu')

def get_nepal_time():
    """Get current time in Nepal Timezone (NPT)"""
    return datetime.now(NEPAL_TZ)

def convert_to_nepal_time(dt):
    """Convert UTC datetime to Nepal Timezone"""
    if dt is None:
        return None
    # If datetime is naive (no timezone), assume it's UTC
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    return dt.astimezone(NEPAL_TZ)

def format_nepal_time(dt, format_str='%Y-%m-%d %H:%M:%S'):
    """Format datetime in Nepal Timezone"""
    if dt is None:
        return 'N/A'
    nepal_dt = convert_to_nepal_time(dt)
    return nepal_dt.strftime(format_str)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: get_nepal_time())
    orders = db.relationship('Order', backref='user', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    original_price = db.Column(db.Float, nullable=True)
    discount_percent = db.Column(db.Integer, default=0)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(200), nullable=True)
    stock = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=lambda: get_nepal_time())

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    product = db.relationship('Product')

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    shipping_address = db.Column(db.Text, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: get_nepal_time())
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    product = db.relationship('Product')

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: get_nepal_time())
    
    product = db.relationship('Product', backref='reviews')
    user = db.relationship('User', backref='reviews')
    
    # Relationships
    product = db.relationship('Product', backref='reviews')
    user = db.relationship('User', backref='reviews')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def send_otp_email(email, otp):
    """Send OTP to user's email - Mobile Responsive"""
    try:
        msg = Message('Email Verification - Dhami Electronics', recipients=[email])
        msg.html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>Email Verification - Dhami Electronics</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f5f5f5;
            margin: 0;
            padding: 10px;
            -webkit-font-smoothing: antialiased;
        }}
        .email-container {{
            max-width: 500px;
            width: 100%;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        @media only screen and (max-width: 600px) {{
            body {{
                padding: 0;
            }}
            .email-container {{
                width: 100%;
                border-radius: 0;
            }}
            .content-padding {{
                padding: 20px !important;
            }}
            .otp-code {{
                font-size: 28px !important;
                padding: 15px !important;
                letter-spacing: 3px !important;
            }}
            .header h1 {{
                font-size: 22px !important;
            }}
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 25px 20px;
            text-align: center;
            color: white;
        }}
        .header h1 {{
            font-size: 24px;
            margin: 0;
            font-weight: 600;
        }}
        .header p {{
            font-size: 13px;
            margin: 5px 0 0;
            opacity: 0.9;
        }}
        .content-padding {{
            padding: 25px;
        }}
        .greeting {{
            font-size: 16px;
            font-weight: 600;
            color: #333;
            margin-bottom: 12px;
        }}
        .message {{
            font-size: 14px;
            color: #555;
            line-height: 1.5;
            margin-bottom: 20px;
        }}
        .otp-code {{
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
            text-align: center;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 12px;
            letter-spacing: 5px;
            margin: 20px 0;
            word-wrap: break-word;
            word-break: break-all;
        }}
        .validity {{
            font-size: 12px;
            color: #999;
            text-align: center;
            margin-top: 15px;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 15px;
            text-align: center;
            font-size: 11px;
            color: #999;
            border-top: 1px solid #e0e0e0;
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            <h1>Dhami Electronics</h1>
            <p>Email Verification</p>
        </div>
        
        <div class="content-padding">
            <div class="greeting">Hello!</div>
            <div class="message">
                Thank you for registering with Dhami Electronics. Please use the following OTP to verify your email address:
            </div>
            
            <div class="otp-code">
                <strong>{otp}</strong>
            </div>
            
            <div class="validity">
                ⏰ This OTP is valid for 10 minutes
            </div>
        </div>
        
        <div class="footer">
            <p>© 2026 Dhami Electronics. All rights reserved.</p>
            <p style="font-size: 10px;">This is an automated message, please do not reply.</p>
        </div>
    </div>
</body>
</html>'''
        mail.send(msg)
        print(f"OTP email sent to {email}")
        return True
    except Exception as e:
        print(f"Error sending OTP email: {str(e)}")
        return False


def send_order_notification_to_admin(order, user, order_items, total_amount, shipping_address, phone):
    """Send order notification email to admin - Mobile Responsive"""
    try:
        # Helper function to truncate long product names
        def truncate_text(text, max_length=50):
            if len(text) > max_length:
                return text[:max_length] + '...'
            return text
        
        subtotal = total_amount - calculate_shipping(total_amount)
        shipping = calculate_shipping(subtotal)
        shipping_display = 'FREE' if shipping == 0 else f'NPR {shipping:.0f}'
        
        # Build order items HTML
        items_html = ""
        for item in order_items:
            product_name = truncate_text(item.product.name, 45)
            items_html += f'''
            <div style="padding: 10px 0; border-bottom: 1px solid #e0e0e0;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; flex-wrap: wrap;">
                    <div style="flex: 2; min-width: 150px;">
                        <div style="font-size: 13px; color: #333; line-height: 1.4; word-wrap: break-word; word-break: break-word;">{product_name}</div>
                        <div style="font-size: 11px; color: #999; margin-top: 4px;">Quantity: {item.quantity}</div>
                    </div>
                    <div style="font-weight: 600; color: #667eea; font-size: 13px; white-space: nowrap;">
                        NPR {item.price * item.quantity:.0f}
                    </div>
                </div>
            </div>
            '''
        
        msg = Message(
            f'🛍️ NEW ORDER #{order.id} - Dhami Electronics', 
            recipients=[ADMIN_EMAIL]
        )
        
        msg.html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>New Order Notification</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f5f5f5;
            margin: 0;
            padding: 10px;
            -webkit-font-smoothing: antialiased;
        }}
        .email-container {{
            max-width: 550px;
            width: 100%;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        @media only screen and (max-width: 600px) {{
            body {{
                padding: 0;
            }}
            .email-container {{
                width: 100%;
                border-radius: 0;
            }}
            .content-padding {{
                padding: 16px !important;
            }}
            .header h1 {{
                font-size: 20px !important;
            }}
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            text-align: center;
            color: white;
        }}
        .header h1 {{
            font-size: 22px;
            margin: 0;
        }}
        .header p {{
            font-size: 13px;
            margin: 5px 0 0;
            opacity: 0.9;
        }}
        .content-padding {{
            padding: 20px;
        }}
        .info-box {{
            background: #f8f9fa;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            font-size: 13px;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .info-label {{
            font-weight: 600;
            color: #555;
            min-width: 100px;
        }}
        .info-value {{
            color: #333;
            text-align: right;
            word-wrap: break-word;
            word-break: break-word;
            flex: 1;
        }}
        .section-title {{
            font-size: 15px;
            font-weight: 600;
            color: #333;
            margin: 20px 0 12px 0;
            padding-bottom: 6px;
            border-bottom: 2px solid #f0f0f0;
        }}
        .price-breakdown {{
            background: #f8f9fa;
            padding: 12px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .price-row {{
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            font-size: 13px;
        }}
        .total-row {{
            border-top: 1px solid #ddd;
            margin-top: 8px;
            padding-top: 10px;
            font-weight: 700;
            font-size: 15px;
        }}
        .status-badge {{
            display: inline-block;
            background: #ffc107;
            color: #333;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 15px;
            text-align: center;
            font-size: 11px;
            color: #999;
            border-top: 1px solid #e0e0e0;
        }}
        @media (max-width: 480px) {{
            .info-row {{
                flex-direction: column;
                align-items: flex-start;
            }}
            .info-value {{
                text-align: left;
                width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            <h1>🛍️ New Order Received!</h1>
            <p>Order #{order.id}</p>
        </div>
        
        <div class="content-padding">
            <div class="info-box">
                <div class="info-row">
                    <span class="info-label">👤 Customer Name:</span>
                    <span class="info-value">{user.username}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">📧 Email:</span>
                    <span class="info-value">{user.email}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">📞 Phone:</span>
                    <span class="info-value">{phone}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">📍 Shipping Address:</span>
                    <span class="info-value">{shipping_address}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">📅 Order Date:</span>
                    <span class="info-value">{order.created_at.strftime('%b %d, %Y')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">📊 Order Status:</span>
                    <span class="info-value"><span class="status-badge">{order.status.upper()}</span></span>
                </div>
            </div>
            
            <div class="section-title">📦 Order Items</div>
            {items_html}
            
            <div class="price-breakdown">
                <div class="price-row">
                    <span>Subtotal:</span>
                    <span>NPR {subtotal:.0f}</span>
                </div>
                <div class="price-row">
                    <span>Shipping Fee:</span>
                    <span>{shipping_display}</span>
                </div>
                <div class="price-row total-row">
                    <span>Grand Total:</span>
                    <span style="color: #667eea;">NPR {total_amount:.0f}</span>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>© 2026 Dhami Electronics. All rights reserved.</p>
            <p>This is an automated notification for admin</p>
        </div>
    </div>
</body>
</html>'''
        mail.send(msg)
        print(f"Order notification sent to admin: {ADMIN_EMAIL}")
        return True
    except Exception as e:
        print(f"Error sending order notification to admin: {str(e)}")
        return False


def send_order_confirmation_to_customer(order, user, order_items, total_amount, shipping_address, phone):
    """Send order confirmation email to customer - Mobile Responsive"""
    try:
        # Helper function to truncate long product names
        def truncate_text(text, max_length=50):
            if len(text) > max_length:
                return text[:max_length] + '...'
            return text
        
        subtotal = total_amount - calculate_shipping(total_amount)
        shipping = calculate_shipping(subtotal)
        shipping_display = 'FREE' if shipping == 0 else f'NPR {shipping:.0f}'
        
        # Free shipping message
        if shipping == 0:
            free_shipping_message = '''
            <div style="background: #d4edda; padding: 12px; border-radius: 8px; margin: 20px 0; text-align: center; border-left: 3px solid #28a745;">
                <div style="color: #155724; font-weight: 600; font-size: 13px;">🎉 Free Shipping Applied!</div>
                <div style="color: #155724; font-size: 11px; margin-top: 4px;">You've qualified for free shipping on this order.</div>
            </div>
            '''
        else:
            free_shipping_message = '''
            <div style="background: #fff3cd; padding: 12px; border-radius: 8px; margin: 20px 0; text-align: center; border-left: 3px solid #ffc107;">
                <div style="color: #856404; font-weight: 600; font-size: 13px;">ℹ️ Shipping Information</div>
                <div style="color: #856404; font-size: 11px; margin-top: 4px;">A flat shipping fee of NPR 150 applies to orders under NPR 5000.</div>
            </div>
            '''
        
        # Build order items HTML
        items_html = ""
        for item in order_items:
            product_name = truncate_text(item.product.name, 45)
            items_html += f'''
            <div style="padding: 10px 0; border-bottom: 1px solid #e0e0e0;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; flex-wrap: wrap;">
                    <div style="flex: 2; min-width: 150px;">
                        <div style="font-size: 13px; color: #333; line-height: 1.4; word-wrap: break-word; word-break: break-word;">{product_name}</div>
                        <div style="font-size: 11px; color: #999; margin-top: 4px;">Quantity: {item.quantity}</div>
                    </div>
                    <div style="font-weight: 600; color: #28a745; font-size: 13px; white-space: nowrap;">
                        NPR {item.price * item.quantity:.0f}
                    </div>
                </div>
            </div>
            '''
        
        msg = Message(
            f'✅ Order Confirmation #{order.id} - Dhami Electronics', 
            recipients=[user.email]
        )
        
        msg.html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>Order Confirmation - Dhami Electronics</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f5f5f5;
            margin: 0;
            padding: 10px;
            -webkit-font-smoothing: antialiased;
        }}
        .email-container {{
            max-width: 550px;
            width: 100%;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        @media only screen and (max-width: 600px) {{
            body {{
                padding: 0;
            }}
            .email-container {{
                width: 100%;
                border-radius: 0;
            }}
            .content-padding {{
                padding: 16px !important;
            }}
            .header h1 {{
                font-size: 20px !important;
            }}
        }}
        .header {{
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            padding: 20px;
            text-align: center;
            color: white;
        }}
        .header h1 {{
            font-size: 22px;
            margin: 0;
        }}
        .header p {{
            font-size: 13px;
            margin: 5px 0 0;
            opacity: 0.9;
        }}
        .content-padding {{
            padding: 20px;
        }}
        .greeting {{
            font-size: 15px;
            font-weight: 600;
            color: #333;
            margin-bottom: 15px;
        }}
        .info-box {{
            background: #f8f9fa;
            padding: 12px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            font-size: 13px;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .info-label {{
            font-weight: 600;
            color: #555;
            min-width: 100px;
        }}
        .info-value {{
            color: #333;
            text-align: right;
            word-wrap: break-word;
            word-break: break-word;
            flex: 1;
        }}
        .section-title {{
            font-size: 15px;
            font-weight: 600;
            color: #333;
            margin: 20px 0 12px 0;
            padding-bottom: 6px;
            border-bottom: 2px solid #f0f0f0;
        }}
        .price-breakdown {{
            background: #f8f9fa;
            padding: 12px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .price-row {{
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            font-size: 13px;
        }}
        .total-row {{
            border-top: 1px solid #ddd;
            margin-top: 8px;
            padding-top: 10px;
            font-weight: 700;
            font-size: 15px;
        }}
        .delivery-note {{
            background: #e8f5e9;
            padding: 12px;
            border-radius: 8px;
            margin: 20px 0;
            text-align: center;
        }}
        .delivery-text {{
            font-size: 12px;
            color: #2e7d32;
            line-height: 1.4;
        }}
        .support-box {{
            background: #fff8e1;
            padding: 12px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 3px solid #E66239;
        }}
        .support-title {{
            font-weight: 600;
            color: #E66239;
            margin-bottom: 6px;
            font-size: 12px;
        }}
        .support-text {{
            font-size: 12px;
            color: #555;
            line-height: 1.4;
        }}
        .support-text a {{
            color: #E66239;
            text-decoration: none;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 15px;
            text-align: center;
            font-size: 11px;
            color: #999;
            border-top: 1px solid #e0e0e0;
        }}
        .button {{
            display: block;
            background: #28a745;
            color: white;
            padding: 12px;
            text-decoration: none;
            border-radius: 8px;
            text-align: center;
            font-size: 14px;
            font-weight: 500;
            margin: 20px 0 10px;
        }}
        @media (max-width: 480px) {{
            .info-row {{
                flex-direction: column;
                align-items: flex-start;
            }}
            .info-value {{
                text-align: left;
                width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            <h1>✅ Order Confirmed!</h1>
            <p>Thank you for shopping with Dhami Electronics</p>
        </div>
        
        <div class="content-padding">
            <div class="greeting">
                Dear {user.username},
            </div>
            
            <div class="info-box">
                <div class="info-row">
                    <span class="info-label">📋 Order #:</span>
                    <span class="info-value">{order.id}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">📅 Order Date:</span>
                    <span class="info-value">{order.created_at.strftime('%b %d, %Y')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">📍 Shipping Address:</span>
                    <span class="info-value">{shipping_address}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">📞 Phone:</span>
                    <span class="info-value">{phone}</span>
                </div>
            </div>
            
            <div class="section-title">📦 Order Items</div>
            {items_html}
            
            <div class="price-breakdown">
                <div class="price-row">
                    <span>Subtotal:</span>
                    <span>NPR {subtotal:.0f}</span>
                </div>
                <div class="price-row">
                    <span>Shipping Fee:</span>
                    <span>{shipping_display}</span>
                </div>
                <div class="price-row total-row">
                    <span>Grand Total:</span>
                    <span style="color: #28a745;">NPR {total_amount:.0f}</span>
                </div>
            </div>
            
            {free_shipping_message}
            
            <div class="delivery-note">
                <div class="delivery-text">
                    🚚 Your order will be delivered within 3-5 business days.<br>
                    You can track your order status in your account dashboard.
                </div>
            </div>
            
            <div class="support-box">
                <div class="support-title">📞 Need Assistance?</div>
                <div class="support-text">
                    📧 <a href="mailto:noreply.dhamielectronics@gmail.com">support@dhamielectronics.com</a><br>
                    📱 +977-9866109958<br>
                    ⏰ 10:00 AM - 6:00 PM (Sun-Fri)
                </div>
            </div>
            
            
        </div>
        
        <div class="footer">
            <p>© 2026 Dhami Electronics. All rights reserved.</p>
            <p style="font-size: 10px;">This is an automated message, please do not reply.</p>
        </div>
    </div>
</body>
</html>'''
        mail.send(msg)
        print(f"Order confirmation sent to customer: {user.email}")
        return True
    except Exception as e:
        print(f"Error sending confirmation email to customer: {str(e)}")
        return False
# Routes
@app.route('/')
def index():
    # Order by newest first using created_at
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('index.html', products=products)

@app.route('/product/<int:id>', methods=['GET', 'POST'])
def product_detail(id):
    product = Product.query.get_or_404(id)
    
    # Handle review submission
    if request.method == 'POST' and current_user.is_authenticated:
        rating = request.form.get('rating')
        comment = request.form.get('comment')
        
        if rating and int(rating) >= 1 and int(rating) <= 5:
            # Check if user already reviewed this product
            existing_review = Review.query.filter_by(
                product_id=product.id, 
                user_id=current_user.id
            ).first()
            
            if existing_review:
                flash('You have already reviewed this product!', 'warning')
            else:
                review = Review(
                    product_id=product.id,
                    user_id=current_user.id,
                    rating=int(rating),
                    comment=comment
                )
                db.session.add(review)
                db.session.commit()
                flash('Thank you for your review!', 'success')
        else:
            flash('Please select a valid rating!', 'danger')
        
        return redirect(url_for('product_detail', id=product.id))
    
    # Get all reviews for this product
    reviews = Review.query.filter_by(product_id=product.id).order_by(Review.created_at.desc()).all()
    
    # Calculate average rating
    avg_rating = 0
    if reviews:
        avg_rating = sum(r.rating for r in reviews) / len(reviews)
    
    return render_template('product_detail.html', product=product, reviews=reviews, avg_rating=avg_rating)

@app.route('/add_to_cart/<int:product_id>')
@login_required
def add_to_cart(product_id):
    if not current_user.is_verified:
        flash('Please verify your email before purchasing!', 'warning')
        return redirect(url_for('verify_email_page'))
    
    product = Product.query.get_or_404(product_id)
    
    if product.stock <= 0:
        flash('Sorry! This product is out of stock.', 'danger')
        return redirect(url_for('product_detail', id=product_id))
    
    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if cart_item:
        if cart_item.quantity + 1 > product.stock:
            flash(f'Sorry! Only {product.stock} items available in stock.', 'danger')
            return redirect(url_for('cart'))
        cart_item.quantity += 1
    else:
        cart_item = Cart(user_id=current_user.id, product_id=product_id, quantity=1)
        db.session.add(cart_item)
    
    db.session.commit()
    flash('Product added to cart!', 'success')
    return redirect(url_for('cart'))

@app.route('/cart')
@login_required
def cart():
    if not current_user.is_verified:
        flash('Please verify your email to access cart!', 'warning')
        return redirect(url_for('verify_email_page'))
    
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/update_cart/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    cart_item = Cart.query.get_or_404(item_id)
    if cart_item.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    quantity = int(request.json.get('quantity', 1))
    
    if quantity > cart_item.product.stock:
        return jsonify({
            'error': f'Sorry! Only {cart_item.product.stock} items available in stock.',
            'max_stock': cart_item.product.stock
        }), 400
    
    if quantity > 0:
        cart_item.quantity = quantity
        db.session.commit()
        # Return item_total for the updated item
        item_total = cart_item.product.price * cart_item.quantity
        return jsonify({
            'success': True,
            'new_total': sum(item.product.price * item.quantity for item in Cart.query.filter_by(user_id=current_user.id).all()),
            'item_total': item_total
        })
    else:
        # Remove the item completely
        db.session.delete(cart_item)
        db.session.commit()
        # Return success without item_total (item is gone)
        return jsonify({
            'success': True,
            'new_total': sum(item.product.price * item.quantity for item in Cart.query.filter_by(user_id=current_user.id).all()),
            'removed': True  # Flag indicating item was removed
        })

@app.route('/remove_from_cart/<int:item_id>')
@login_required
def remove_from_cart(item_id):
    cart_item = Cart.query.get_or_404(item_id)
    if cart_item.user_id == current_user.id:
        db.session.delete(cart_item)
        db.session.commit()
        flash('Item removed from cart!', 'success')
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if not current_user.is_verified:
        flash('Please verify your email to checkout!', 'warning')
        return redirect(url_for('verify_email_page'))
    
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('index'))
    
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    shipping_fee = calculate_shipping(subtotal)
    total = subtotal + shipping_fee
    
    if request.method == 'POST':
        shipping_address = request.form.get('address')
        phone = request.form.get('phone')
        
        order = Order(user_id=current_user.id, total_amount=total, 
                     status='pending', shipping_address=shipping_address, phone=phone)
        db.session.add(order)
        db.session.commit()
        
        order_items = []
        for item in cart_items:
            order_item = OrderItem(order_id=order.id, product_id=item.product_id, 
                                   quantity=item.quantity, price=item.product.price)
            db.session.add(order_item)
            order_items.append(order_item)
            item.product.stock -= item.quantity
            db.session.delete(item)
        
        db.session.commit()
        
        send_order_notification_to_admin(order, current_user, order_items, total, shipping_address, phone)
        send_order_confirmation_to_customer(order, current_user, order_items, total, shipping_address, phone)
        
        flash('Order placed successfully! Check your email for confirmation.', 'success')
        return redirect(url_for('orders'))
    
    return render_template('checkout.html', cart_items=cart_items, subtotal=subtotal, shipping_fee=shipping_fee, total=total)

@app.route('/add_to_cart_ajax/<int:product_id>')
@login_required
def add_to_cart_ajax(product_id):
    if not current_user.is_verified:
        return jsonify({'success': False, 'message': 'Please verify your email first!'}), 400
    
    product = Product.query.get_or_404(product_id)
    
    if product.stock <= 0:
        return jsonify({'success': False, 'message': 'Sorry! This product is out of stock.'}), 400
    
    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if cart_item:
        if cart_item.quantity + 1 > product.stock:
            return jsonify({'success': False, 'message': f'Sorry! Only {product.stock} items available in stock.'}), 400
        cart_item.quantity += 1
    else:
        cart_item = Cart(user_id=current_user.id, product_id=product_id, quantity=1)
        db.session.add(cart_item)
    
    db.session.commit()
    cart_count = Cart.query.filter_by(user_id=current_user.id).count()
    
    return jsonify({'success': True, 'message': f'{product.name} added to cart!', 'cart_count': cart_count})

@app.route('/get_cart_count')
@login_required
def get_cart_count():
    cart_count = Cart.query.filter_by(user_id=current_user.id).count()
    return jsonify({'count': cart_count})

@app.route('/orders')
@login_required
def orders():
    from datetime import datetime
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=user_orders, now=datetime)

@app.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('index'))
    return render_template('order_detail.html', order=order)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not is_valid_email(email):
            flash('Invalid email format!', 'danger')
            return redirect(url_for('register'))
        
        user_exists = User.query.filter_by(username=username).first()
        email_exists = User.query.filter_by(email=email).first()
        
        if user_exists:
            flash('Username already exists!', 'danger')
        elif email_exists:
            flash('Email already registered!', 'danger')
        else:
            otp = str(random.randint(100000, 999999))
            
            if send_otp_email(email, otp):
                session['temp_user'] = {
                    'username': username,
                    'email': email,
                    'password': generate_password_hash(password),
                    'otp': otp,
                    'otp_created_at': datetime.now().timestamp()
                }
                flash('OTP sent to your email! Please verify.', 'info')
                return redirect(url_for('verify_otp'))
            else:
                flash('Failed to send OTP. Please try again.', 'danger')
    
    return render_template('register.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'temp_user' not in session:
        flash('Please register first!', 'warning')
        return redirect(url_for('register'))
    
    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        temp_user = session['temp_user']
        
        otp_age = datetime.now().timestamp() - temp_user['otp_created_at']
        if otp_age > 600:
            session.pop('temp_user', None)
            flash('OTP expired! Please register again.', 'danger')
            return redirect(url_for('register'))
        
        if entered_otp == temp_user['otp']:
            new_user = User(
                username=temp_user['username'],
                email=temp_user['email'],
                password=temp_user['password'],
                is_verified=True
            )
            db.session.add(new_user)
            db.session.commit()
            
            session.pop('temp_user', None)
            flash('Email verified successfully! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid OTP! Please try again.', 'danger')
    
    return render_template('verify_otp.html', email=session['temp_user']['email'])

@app.route('/resend-otp')
def resend_otp():
    if 'temp_user' in session:
        temp_user = session['temp_user']
        new_otp = str(random.randint(100000, 999999))
        
        if send_otp_email(temp_user['email'], new_otp):
            temp_user['otp'] = new_otp
            temp_user['otp_created_at'] = datetime.now().timestamp()
            session['temp_user'] = temp_user
            return jsonify({'success': True, 'message': 'New OTP sent!'})
        else:
            return jsonify({'error': 'Failed to send OTP'}), 500
    
    elif 'reset_otp' in session:
        reset_data = session['reset_otp']
        new_otp = str(random.randint(100000, 999999))
        
        if send_password_reset_email(reset_data['email'], new_otp):
            reset_data['otp'] = new_otp
            reset_data['created_at'] = datetime.now().timestamp()
            session['reset_otp'] = reset_data
            return jsonify({'success': True, 'message': 'New OTP sent!'})
        else:
            return jsonify({'error': 'Failed to send OTP'}), 500
    
    else:
        return jsonify({'error': 'No registration or password reset in progress'}), 400

@app.route('/verify-email-page')
@login_required
def verify_email_page():
    if current_user.is_verified:
        flash('Your email is already verified!', 'info')
        return redirect(url_for('index'))
    return render_template('verify_email_prompt.html')

@app.route('/send-verification-email')
@login_required
def send_verification_email():
    if current_user.is_verified:
        return jsonify({'error': 'Already verified'}), 400
    
    otp = str(random.randint(100000, 999999))
    
    session['verify_otp'] = {
        'otp': otp,
        'created_at': datetime.now().timestamp()
    }
    
    if send_otp_email(current_user.email, otp):
        return jsonify({'success': True, 'message': 'Verification email sent!'})
    else:
        return jsonify({'error': 'Failed to send email'}), 500

@app.route('/verify-user-otp', methods=['POST'])
@login_required
def verify_user_otp():
    if current_user.is_verified:
        return jsonify({'error': 'Already verified'}), 400
    
    entered_otp = request.json.get('otp')
    verify_data = session.get('verify_otp', {})
    
    if not verify_data:
        return jsonify({'error': 'No OTP request found'}), 400
    
    if datetime.now().timestamp() - verify_data['created_at'] > 600:
        session.pop('verify_otp', None)
        return jsonify({'error': 'OTP expired'}), 400
    
    if entered_otp == verify_data['otp']:
        current_user.is_verified = True
        db.session.commit()
        session.pop('verify_otp', None)
        return jsonify({'success': True, 'message': 'Email verified successfully!'})
    else:
        return jsonify({'error': 'Invalid OTP'}), 400

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_input = request.form.get('username')
        password = request.form.get('password')
        
        user = None
        if '@' in login_input and '.' in login_input:
            user = User.query.filter_by(email=login_input).first()
        else:
            user = User.query.filter_by(username=login_input).first()
        
        if not user:
            if '@' in login_input and '.' in login_input:
                user = User.query.filter_by(username=login_input).first()
            else:
                user = User.query.filter_by(email=login_input).first()
        
        if user and check_password_hash(user.password, password):
            if not user.is_verified:
                flash('Please verify your email before logging in!', 'warning')
                return redirect(url_for('verify_email_page'))
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email/username or password!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('index'))
    
    # Order products by newest first
    products = Product.query.order_by(Product.created_at.desc()).all()
    users = User.query.all()
    orders = Order.query.order_by(Order.created_at.desc()).all()
    pending_orders = Order.query.filter_by(status='pending').count()
    
    return render_template('admin/dashboard.html', 
                         products=products, users=users, orders=orders,
                         pending_orders=pending_orders)

@app.route('/admin/orders')
@login_required
def admin_orders():
    if not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('index'))
    
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/order/<int:order_id>')
@login_required
def admin_order_detail(order_id):
    if not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('index'))
    
    order = Order.query.get_or_404(order_id)
    return render_template('admin/order_detail.html', order=order)

@app.route('/admin/update_order_status/<int:order_id>', methods=['POST'])
@login_required
def update_order_status(order_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    order = Order.query.get_or_404(order_id)
    new_status = request.json.get('status')
    
    if new_status in ['pending', 'processing', 'shipped', 'delivered', 'cancelled']:
        order.status = new_status
        db.session.commit()
        
        # Send status update email to customer
        try:
            # Status specific content
            status_content = {
                'processing': {
                    'color': '#17a2b8',
                    'bg_color': '#e1f5fe',
                    'icon': '⚙️',
                    'title': 'Order is Being Processed',
                    'message': 'Great news! Your order has been received and is now being processed.'
                },
                'shipped': {
                    'color': '#007bff',
                    'bg_color': '#e3f2fd',
                    'icon': '🚚',
                    'title': 'Order Has Been Shipped!',
                    'message': 'Your order is on the way! Our delivery partner has picked up your package.'
                },
                'delivered': {
                    'color': '#28a745',
                    'bg_color': '#e8f5e9',
                    'icon': '✅',
                    'title': 'Order Delivered Successfully!',
                    'message': 'Your order has been delivered! We hope you enjoy your purchase.'
                },
                'cancelled': {
                    'color': '#dc3545',
                    'bg_color': '#ffebee',
                    'icon': '❌',
                    'title': 'Order Cancelled',
                    'message': 'Your order has been cancelled as requested.'
                },
                'pending': {
                    'color': '#ffc107',
                    'bg_color': '#fff3e0',
                    'icon': '⏳',
                    'title': 'Order Confirmed',
                    'message': 'Your order has been confirmed and is awaiting processing.'
                }
            }
            
            content = status_content.get(new_status, status_content['pending'])
            
            # Calculate shipping info
            subtotal = order.total_amount - calculate_shipping(order.total_amount)
            shipping = calculate_shipping(subtotal)
            shipping_display = 'FREE' if shipping == 0 else f'NPR {shipping:.0f}'
            
            # Helper function to truncate long product names
            def truncate_text(text, max_length=50):
                if len(text) > max_length:
                    return text[:max_length] + '...'
                return text
            
            # Build order items HTML with proper wrapping
            items_html = ""
            for item in order.items:
                product_name = item.product.name if item.product else "Product Unavailable"
                truncated_name = truncate_text(product_name, 45)
                items_html += f'''
                <div style="padding: 12px 0; border-bottom: 1px solid #e0e0e0;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; flex-wrap: wrap;">
                        <div style="flex: 2; min-width: 150px;">
                            <div style="font-size: 14px; color: #333; line-height: 1.4; word-wrap: break-word; word-break: break-word;">{truncated_name}</div>
                            <div style="font-size: 11px; color: #999; margin-top: 4px;">Quantity: {item.quantity}</div>
                        </div>
                        <div style="font-weight: 600; color: #E66239; font-size: 14px; white-space: nowrap;">
                            NPR {item.price * item.quantity:.0f}
                        </div>
                    </div>
                </div>
                '''
            
            # Mobile-friendly HTML email
            msg = Message(
                f'Order #{order.id} Status Update - Dhami Electronics', 
                recipients=[order.user.email]
            )
            
            msg.html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>Order Status Update</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f5f5f5;
            margin: 0;
            padding: 10px;
            -webkit-font-smoothing: antialiased;
        }}
        .email-container {{
            max-width: 550px;
            width: 100%;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        @media only screen and (max-width: 600px) {{
            body {{
                padding: 0;
            }}
            .email-container {{
                width: 100%;
                border-radius: 0;
            }}
            .content-padding {{
                padding: 16px !important;
            }}
            .header h1 {{
                font-size: 20px !important;
            }}
            .header p {{
                font-size: 12px !important;
            }}
        }}
        .header {{
            background: {content['color']};
            padding: 20px;
            text-align: center;
            color: white;
        }}
        .header h1 {{
            font-size: 22px;
            margin: 0;
        }}
        .header p {{
            font-size: 13px;
            margin: 5px 0 0;
            opacity: 0.9;
        }}
        .content-padding {{
            padding: 20px;
        }}
        .status-box {{
            background: {content['bg_color']};
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 20px;
        }}
        .status-badge {{
            display: inline-block;
            background: {content['color']};
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            margin-bottom: 10px;
        }}
        .status-title {{
            font-size: 17px;
            font-weight: 600;
            color: #333;
            margin: 8px 0;
        }}
        .status-message {{
            font-size: 13px;
            color: #666;
            line-height: 1.4;
        }}
        .info-box {{
            background: #f8f9fa;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            font-size: 13px;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .info-label {{
            font-weight: 600;
            color: #555;
            min-width: 100px;
        }}
        .info-value {{
            color: #333;
            text-align: right;
            word-wrap: break-word;
            word-break: break-word;
            flex: 1;
        }}
        .section-title {{
            font-size: 15px;
            font-weight: 600;
            color: #333;
            margin: 20px 0 12px 0;
            padding-bottom: 6px;
            border-bottom: 2px solid #f0f0f0;
        }}
        .price-breakdown {{
            background: #f8f9fa;
            padding: 12px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .price-row {{
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            font-size: 13px;
        }}
        .total-row {{
            border-top: 1px solid #ddd;
            margin-top: 8px;
            padding-top: 10px;
            font-weight: 700;
            font-size: 15px;
        }}
        .support-box {{
            background: #fff8e1;
            padding: 12px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 3px solid #E66239;
        }}
        .support-title {{
            font-weight: 600;
            color: #E66239;
            margin-bottom: 6px;
            font-size: 12px;
        }}
        .support-text {{
            font-size: 12px;
            color: #555;
            line-height: 1.4;
        }}
        .support-text a {{
            color: #E66239;
            text-decoration: none;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 15px;
            text-align: center;
            font-size: 11px;
            color: #999;
            border-top: 1px solid #e0e0e0;
        }}
        .button {{
            display: block;
            background: {content['color']};
            color: white;
            padding: 12px;
            text-decoration: none;
            border-radius: 8px;
            text-align: center;
            font-size: 14px;
            font-weight: 500;
            margin: 20px 0 10px;
        }}
        @media (max-width: 480px) {{
            .info-row {{
                flex-direction: column;
                align-items: flex-start;
            }}
            .info-value {{
                text-align: left;
                width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            <h1>{content['icon']} {content['title']}</h1>
            <p>Order #{order.id}</p>
        </div>
        
        <div class="content-padding">
            <!-- Status Box -->
            <div class="status-box">
                <div class="status-badge">{new_status.upper()}</div>
                <div class="status-title">{content['title']}</div>
                <div class="status-message">{content['message']}</div>
            </div>
            
            <!-- Order Info -->
            <div class="info-box">
                <div class="info-row">
                    <span class="info-label">📅 Order Date:</span>
                    <span class="info-value">{order.created_at.strftime('%b %d, %Y')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">📍 Shipping Address:</span>
                    <span class="info-value">{order.shipping_address or 'Not provided'}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">📞 Phone:</span>
                    <span class="info-value">{order.phone or 'Not provided'}</span>
                </div>
            </div>
            
            <!-- Order Items -->
            <div class="section-title">📦 Order Items</div>
            {items_html}
            
            <!-- Price Breakdown -->
            <div class="price-breakdown">
                <div class="price-row">
                    <span>Subtotal:</span>
                    <span>NPR {subtotal:.0f}</span>
                </div>
                <div class="price-row">
                    <span>Shipping Fee:</span>
                    <span>{shipping_display}</span>
                </div>
                <div class="price-row total-row">
                    <span>Total Amount:</span>
                    <span style="color: {content['color']};">NPR {order.total_amount:.0f}</span>
                </div>
            </div>
            
            <!-- Support Box -->
            <div class="support-box">
                <div class="support-title">📞 Need Assistance?</div>
                <div class="support-text">
                    📧 <a href="mailto:noreply.dhamielectronics@gmail.com">support@dhamielectronics.com</a><br>
                    📱 +977-9866109958<br>
                    ⏰ 10:00 AM - 6:00 PM (Sun-Fri)
                </div>
            </div>
            
            <!-- View Order Button -->
          
        </div>
        
        <div class="footer">
            <p>© 2026 Dhami Electronics. All rights reserved.</p>
            <p style="font-size: 10px;">This is an automated message, please do not reply.</p>
        </div>
    </div>
</body>
</html>'''
            
            mail.send(msg)
            print(f"Status update email sent to {order.user.email}")
            
        except Exception as e:
            print(f"Error sending status update: {str(e)}")
        
        return jsonify({'success': True, 'message': f'Order status updated to {new_status}!'})
    
    return jsonify({'error': 'Invalid status'}), 400

@app.route('/admin/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        price = float(request.form.get('price'))
        original_price = request.form.get('original_price')
        discount_percent = int(request.form.get('discount_percent', 0))
        description = request.form.get('description')
        category = request.form.get('category')
        stock = int(request.form.get('stock'))
        
        if original_price and float(original_price) > 0:
            original_price = float(original_price)
        else:
            original_price = price
        
        file = request.files['image']
        filename = None
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = f"{datetime.now().timestamp()}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        product = Product(
            name=name, 
            price=price, 
            original_price=original_price,
            discount_percent=discount_percent,
            description=description, 
            category=category, 
            stock=stock, 
            image=filename
        )
        db.session.add(product)
        db.session.commit()
        
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/add_product.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/returns-policy')
def returns_policy():
    return render_template('returns_policy.html')

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/admin/edit_product/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    if not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('index'))
    
    product = Product.query.get_or_404(id)
    
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.price = float(request.form.get('price'))
        product.original_price = float(request.form.get('original_price')) if request.form.get('original_price') else product.price
        product.discount_percent = int(request.form.get('discount_percent', 0))
        product.description = request.form.get('description')
        product.category = request.form.get('category')
        product.stock = int(request.form.get('stock'))
        
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = f"{datetime.now().timestamp()}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            product.image = filename
        
        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/edit_product.html', product=product)

@app.route('/admin/delete_product/<int:id>')
@login_required
def delete_product(id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    product = Product.query.get_or_404(id)
    
    # Get product name before deleting (for response message)
    product_name = product.name
    
    try:
        # First, delete all reviews associated with this product
        reviews = Review.query.filter_by(product_id=id).all()
        for review in reviews:
            db.session.delete(review)
        
        # Check if product exists in any cart and remove those cart items
        cart_items = Cart.query.filter_by(product_id=id).all()
        for cart_item in cart_items:
            db.session.delete(cart_item)
        
        # Check if product exists in any order items (optional: handle differently)
        # You might want to prevent deletion if product is in completed orders
        order_items = OrderItem.query.filter_by(product_id=id).all()
        if order_items:
            # Instead of blocking deletion, you can mark the product as inactive
            # or just delete the order items (not recommended for completed orders)
            for order_item in order_items:
                db.session.delete(order_item)
        
        # Delete the product image file if exists
        if product.image:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image)
            if os.path.exists(image_path):
                os.remove(image_path)
        
        # Finally, delete the product
        db.session.delete(product)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Product "{product_name}" and its related data deleted successfully!'})
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting product: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/make_admin/<int:id>')
@login_required
def make_admin(id):
    if not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(id)
    user.is_admin = True
    db.session.commit()
    flash(f'{user.username} is now an admin!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/remove_admin/<int:id>')
@login_required
def remove_admin(id):
    if not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(id)
    
    if user.id == current_user.id:
        flash('❌ You cannot remove your own admin privileges!', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    oldest_admin = User.query.filter_by(is_admin=True).order_by(User.id.asc()).first()
    if oldest_admin and user.id == oldest_admin.id:
        flash('❌ Cannot remove the original administrator!', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    admin_count = User.query.filter_by(is_admin=True).count()
    if admin_count <= 1:
        flash('❌ Cannot remove the last admin! There must be at least one admin.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    user.is_admin = False
    db.session.commit()
    flash(f'✅ Admin privileges removed from {user.username}!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/cancel_order/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    """Cancel an order - only allowed within 1 hour of creation and if status is pending/processing"""
    order = Order.query.get_or_404(order_id)
    
    # Check if user owns this order
    if order.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Check if order can be cancelled
    if order.status in ['cancelled', 'delivered', 'shipped']:
        return jsonify({'error': f'Cannot cancel order with status: {order.status}'}), 400
    
    # Check if within 1 hour of creation
    from datetime import datetime, timedelta
    time_diff = datetime.utcnow() - order.created_at
    if time_diff.total_seconds() > 3600:  # 1 hour = 3600 seconds
        return jsonify({'error': 'Orders can only be cancelled within 1 hour of placement. Please contact support.'}), 400
    
    # Cancel the order
    old_status = order.status
    order.status = 'cancelled'
    
    # Restore product stock
    for item in order.items:
        product = Product.query.get(item.product_id)
        if product:
            product.stock += item.quantity
    
    db.session.commit()
    
    # Send cancellation notification to admin
    try:
        send_order_cancellation_notification(order, current_user)
    except Exception as e:
        print(f"Error sending cancellation notification: {str(e)}")
    
    # Send cancellation confirmation to customer
    try:
        send_cancellation_confirmation_to_customer(order, current_user)
    except Exception as e:
        print(f"Error sending cancellation email to customer: {str(e)}")
    
    return jsonify({'success': True, 'message': 'Order cancelled successfully'})


def send_order_cancellation_notification(order, user):
    """Send cancellation notification email to admin (mobile-responsive)"""
    try:
        # Helper function to truncate long product names
        def truncate_text(text, max_length=50):
            if len(text) > max_length:
                return text[:max_length] + '...'
            return text
        
        # Calculate shipping info
        subtotal = order.total_amount - calculate_shipping(order.total_amount)
        shipping = calculate_shipping(subtotal)
        shipping_display = 'FREE' if shipping == 0 else f'NPR {shipping:.0f}'
        
        # Build order items HTML
        items_html = ""
        for item in order.items:
            product_name = item.product.name if item.product else "Product Unavailable"
            truncated_name = truncate_text(product_name, 45)
            items_html += f'''
            <div style="padding: 12px 0; border-bottom: 1px solid #e0e0e0;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; flex-wrap: wrap;">
                    <div style="flex: 2; min-width: 150px;">
                        <div style="font-size: 14px; color: #333; line-height: 1.4; word-wrap: break-word; word-break: break-word;">{truncated_name}</div>
                        <div style="font-size: 11px; color: #999; margin-top: 4px;">Quantity: {item.quantity}</div>
                    </div>
                    <div style="font-weight: 600; color: #dc2626; font-size: 14px; white-space: nowrap;">
                        NPR {item.price * item.quantity:.0f}
                    </div>
                </div>
            </div>
            '''
        
        msg = Message(
            f'❌ ORDER CANCELLED #{order.id} - Dhami Electronics', 
            recipients=[ADMIN_EMAIL]
        )
        
        msg.html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>Order Cancelled - Admin Notification</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f5f5f5;
            margin: 0;
            padding: 10px;
            -webkit-font-smoothing: antialiased;
        }}
        .email-container {{
            max-width: 550px;
            width: 100%;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        @media only screen and (max-width: 600px) {{
            body {{
                padding: 0;
            }}
            .email-container {{
                width: 100%;
                border-radius: 0;
            }}
            .content-padding {{
                padding: 16px !important;
            }}
            .header h1 {{
                font-size: 20px !important;
            }}
        }}
        .header {{
            background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
            padding: 20px;
            text-align: center;
            color: white;
        }}
        .header h1 {{
            font-size: 22px;
            margin: 0;
        }}
        .header p {{
            font-size: 13px;
            margin: 5px 0 0;
            opacity: 0.9;
        }}
        .content-padding {{
            padding: 20px;
        }}
        .cancelled-badge {{
            display: inline-block;
            background: #fee2e2;
            color: #dc2626;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 20px;
        }}
        .info-box {{
            background: #f8f9fa;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            font-size: 13px;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .info-label {{
            font-weight: 600;
            color: #555;
            min-width: 100px;
        }}
        .info-value {{
            color: #333;
            text-align: right;
            word-wrap: break-word;
            word-break: break-word;
            flex: 1;
        }}
        .section-title {{
            font-size: 15px;
            font-weight: 600;
            color: #333;
            margin: 20px 0 12px 0;
            padding-bottom: 6px;
            border-bottom: 2px solid #f0f0f0;
        }}
        .price-breakdown {{
            background: #f8f9fa;
            padding: 12px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .price-row {{
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            font-size: 13px;
        }}
        .total-row {{
            border-top: 1px solid #ddd;
            margin-top: 8px;
            padding-top: 10px;
            font-weight: 700;
            font-size: 15px;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 15px;
            text-align: center;
            font-size: 11px;
            color: #999;
            border-top: 1px solid #e0e0e0;
        }}
        @media (max-width: 480px) {{
            .info-row {{
                flex-direction: column;
                align-items: flex-start;
            }}
            .info-value {{
                text-align: left;
                width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            <h1>❌ Order Cancelled</h1>
            <p>Order #{order.id} has been cancelled by customer</p>
        </div>
        
        <div class="content-padding">
            <div style="text-align: center;">
                <div class="cancelled-badge">CANCELLED</div>
            </div>
            
            <div class="info-box">
                <div class="info-row">
                    <span class="info-label">👤 Customer Name:</span>
                    <span class="info-value">{user.username}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">📧 Email:</span>
                    <span class="info-value">{user.email}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">📞 Phone:</span>
                    <span class="info-value">{order.phone or 'Not provided'}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">📅 Order Date:</span>
                    <span class="info-value">{order.created_at.strftime('%b %d, %Y')}</span>
                </div>
            </div>
            
            <div class="section-title">📦 Cancelled Items</div>
            {items_html}
            
            <div class="price-breakdown">
                <div class="price-row">
                    <span>Subtotal:</span>
                    <span>NPR {subtotal:.0f}</span>
                </div>
                <div class="price-row">
                    <span>Shipping Fee:</span>
                    <span>{shipping_display}</span>
                </div>
                <div class="price-row total-row">
                    <span>Total Amount Cancelled:</span>
                    <span style="color: #dc2626;">NPR {order.total_amount:.0f}</span>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>© 2026 Dhami Electronics. All rights reserved.</p>
            <p>This is an automated notification for admin</p>
        </div>
    </div>
</body>
</html>'''
        
        mail.send(msg)
        print(f"Cancellation notification sent to admin")
        return True
    except Exception as e:
        print(f"Error sending cancellation notification: {str(e)}")
        return False


def send_cancellation_confirmation_to_customer(order, user):
    """Send cancellation confirmation email to customer (mobile-responsive)"""
    try:
        # Helper function to truncate long product names
        def truncate_text(text, max_length=50):
            if len(text) > max_length:
                return text[:max_length] + '...'
            return text
        
        # Calculate shipping info
        subtotal = order.total_amount - calculate_shipping(order.total_amount)
        shipping = calculate_shipping(subtotal)
        shipping_display = 'FREE' if shipping == 0 else f'NPR {shipping:.0f}'
        
        # Build order items HTML
        items_html = ""
        for item in order.items:
            product_name = item.product.name if item.product else "Product Unavailable"
            truncated_name = truncate_text(product_name, 45)
            items_html += f'''
            <div style="padding: 12px 0; border-bottom: 1px solid #e0e0e0;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; flex-wrap: wrap;">
                    <div style="flex: 2; min-width: 150px;">
                        <div style="font-size: 14px; color: #333; line-height: 1.4; word-wrap: break-word; word-break: break-word;">{truncated_name}</div>
                        <div style="font-size: 11px; color: #999; margin-top: 4px;">Quantity: {item.quantity}</div>
                    </div>
                    <div style="font-weight: 600; color: #dc2626; font-size: 14px; white-space: nowrap;">
                        NPR {item.price * item.quantity:.0f}
                    </div>
                </div>
            </div>
            '''
        
        msg = Message(
            f'Order #{order.id} Cancelled - Dhami Electronics', 
            recipients=[user.email]
        )
        
        msg.html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>Order Cancelled Confirmation</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f5f5f5;
            margin: 0;
            padding: 10px;
            -webkit-font-smoothing: antialiased;
        }}
        .email-container {{
            max-width: 550px;
            width: 100%;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        @media only screen and (max-width: 600px) {{
            body {{
                padding: 0;
            }}
            .email-container {{
                width: 100%;
                border-radius: 0;
            }}
            .content-padding {{
                padding: 16px !important;
            }}
            .header h1 {{
                font-size: 20px !important;
            }}
        }}
        .header {{
            background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
            padding: 20px;
            text-align: center;
            color: white;
        }}
        .header h1 {{
            font-size: 22px;
            margin: 0;
        }}
        .header p {{
            font-size: 13px;
            margin: 5px 0 0;
            opacity: 0.9;
        }}
        .content-padding {{
            padding: 20px;
        }}
        .greeting {{
            font-size: 14px;
            color: #333;
            margin-bottom: 15px;
        }}
        .info-box {{
            background: #f8f9fa;
            padding: 12px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            font-size: 13px;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .info-label {{
            font-weight: 600;
            color: #555;
            min-width: 100px;
        }}
        .info-value {{
            color: #333;
            text-align: right;
            word-wrap: break-word;
            word-break: break-word;
            flex: 1;
        }}
        .section-title {{
            font-size: 15px;
            font-weight: 600;
            color: #333;
            margin: 20px 0 12px 0;
            padding-bottom: 6px;
            border-bottom: 2px solid #f0f0f0;
        }}
        .price-breakdown {{
            background: #f8f9fa;
            padding: 12px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .price-row {{
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            font-size: 13px;
        }}
        .total-row {{
            border-top: 1px solid #ddd;
            margin-top: 8px;
            padding-top: 10px;
            font-weight: 700;
            font-size: 15px;
        }}
        .refund-box {{
            background: #fef2f2;
            padding: 12px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 3px solid #dc2626;
        }}
        .refund-title {{
            font-weight: 600;
            color: #dc2626;
            margin-bottom: 6px;
            font-size: 13px;
        }}
        .refund-text {{
            font-size: 13px;
            color: #555;
            line-height: 1.4;
        }}
        .support-box {{
            background: #fff8e1;
            padding: 12px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 3px solid #E66239;
        }}
        .support-title {{
            font-weight: 600;
            color: #E66239;
            margin-bottom: 6px;
            font-size: 12px;
        }}
        .support-text {{
            font-size: 12px;
            color: #555;
            line-height: 1.4;
        }}
        .support-text a {{
            color: #E66239;
            text-decoration: none;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 15px;
            text-align: center;
            font-size: 11px;
            color: #999;
            border-top: 1px solid #e0e0e0;
        }}
        .button {{
            display: block;
            background: #dc2626;
            color: white;
            padding: 12px;
            text-decoration: none;
            border-radius: 8px;
            text-align: center;
            font-size: 14px;
            font-weight: 500;
            margin: 20px 0 10px;
        }}
        @media (max-width: 480px) {{
            .info-row {{
                flex-direction: column;
                align-items: flex-start;
            }}
            .info-value {{
                text-align: left;
                width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            <h1>❌ Order Cancelled</h1>
            <p>Order #{order.id}</p>
        </div>
        
        <div class="content-padding">
            <div class="greeting">
                Dear {user.username},
            </div>
            
            <p style="font-size: 14px; color: #555; margin-bottom: 20px;">
                Your order has been cancelled as requested.
            </p>
            
            <div class="info-box">
                <div class="info-row">
                    <span class="info-label">📋 Order #:</span>
                    <span class="info-value">{order.id}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">📅 Order Date:</span>
                    <span class="info-value">{order.created_at.strftime('%b %d, %Y')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">📍 Shipping Address:</span>
                    <span class="info-value">{order.shipping_address or 'Not provided'}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">📞 Phone:</span>
                    <span class="info-value">{order.phone or 'Not provided'}</span>
                </div>
            </div>
            
            <div class="section-title">📦 Cancelled Items</div>
            {items_html}
            
            <div class="price-breakdown">
                <div class="price-row">
                    <span>Subtotal:</span>
                    <span>NPR {subtotal:.0f}</span>
                </div>
                <div class="price-row">
                    <span>Shipping Fee:</span>
                    <span>{shipping_display}</span>
                </div>
                <div class="price-row total-row">
                    <span>Total Amount:</span>
                    <span style="color: #dc2626;">NPR {order.total_amount:.0f}</span>
                </div>
            </div>
            
            <div class="refund-box">
                <div class="refund-title">💰 Refund Information</div>
                <div class="refund-text">
                    Your payment of <strong>NPR {order.total_amount:.0f}</strong> will be refunded within 3-5 business days.
                </div>
            </div>
            
            <div class="support-box">
                <div class="support-title">📞 Need Assistance?</div>
                <div class="support-text">
                    📧 <a href="mailto:noreply.dhamielectronics@gmail.com">support@dhamielectronics.com</a><br>
                    📱 +977-9866109958<br>
                    ⏰ 10:00 AM - 6:00 PM (Sun-Fri)
                </div>
            </div>
            
            <a href="#" class="button">View Order Details →</a>
            
            <p style="margin-top: 20px; font-size: 12px; color: #999; text-align: center;">
                Thank you for shopping with Dhami Electronics.
            </p>
        </div>
        
        <div class="footer">
            <p>© 2026 Dhami Electronics. All rights reserved.</p>
            <p style="font-size: 10px;">This is an automated message, please do not reply.</p>
        </div>
    </div>
</body>
</html>'''
        
        mail.send(msg)
        print(f"Cancellation confirmation sent to customer: {user.email}")
        return True
    except Exception as e:
        print(f"Error sending cancellation confirmation: {str(e)}")
        return False
    
# Forgot Password Routes
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            otp = str(random.randint(100000, 999999))
            
            session['reset_otp'] = {
                'email': email,
                'otp': otp,
                'created_at': datetime.now().timestamp()
            }
            
            if send_password_reset_email(email, otp):
                flash('OTP sent to your email! Please verify.', 'info')
                return redirect(url_for('verify_reset_otp'))
            else:
                flash('Failed to send OTP. Please try again.', 'danger')
        else:
            flash('Email not found! Please check your email address.', 'danger')
    
    return render_template('forgot_password.html')

@app.route('/verify-reset-otp', methods=['GET', 'POST'])
def verify_reset_otp():
    if 'reset_otp' not in session:
        flash('Please request password reset first!', 'warning')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        reset_data = session['reset_otp']
        
        if datetime.now().timestamp() - reset_data['created_at'] > 600:
            session.pop('reset_otp', None)
            flash('OTP expired! Please request again.', 'danger')
            return redirect(url_for('forgot_password'))
        
        if entered_otp == reset_data['otp']:
            return redirect(url_for('reset_password'))
        else:
            flash('Invalid OTP! Please try again.', 'danger')
    
    return render_template('verify_reset_otp.html', email=session['reset_otp']['email'])

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_otp' not in session:
        flash('Please verify OTP first!', 'warning')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('reset_password'))
        
        if len(new_password) < 6:
            flash('Password must be at least 6 characters!', 'danger')
            return redirect(url_for('reset_password'))
        
        email = session['reset_otp']['email']
        user = User.query.filter_by(email=email).first()
        
        if user:
            user.password = generate_password_hash(new_password)
            db.session.commit()
            session.pop('reset_otp', None)
            flash('Password reset successfully! Please login with your new password.', 'success')
            return redirect(url_for('login'))
        else:
            flash('User not found!', 'danger')
            return redirect(url_for('forgot_password'))
    
    return render_template('reset_password.html')

def send_password_reset_email(email, otp):
    """Send password reset OTP to user's email"""
    try:
        msg = Message('Password Reset - Dhami Electronics', recipients=[email])
        msg.html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; }}
                .container {{ max-width: 600px; margin: 20px auto; background: white; border-radius: 10px; overflow: hidden; }}
                .header {{ background: #3498db; color: white; padding: 30px; text-align: center; }}
                .content {{ padding: 30px; }}
                .otp-code {{ font-size: 32px; font-weight: bold; color: #3498db; text-align: center; padding: 20px; background: #f8f9fa; border-radius: 8px; letter-spacing: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header"><h1>Password Reset</h1></div>
                <div class="content">
                    <p>You requested to reset your password. Use the following OTP:</p>
                    <div class="otp-code">{otp}</div>
                    <p>This OTP is valid for 10 minutes.</p>
                    <p>If you didn't request this, please ignore this email.</p>
                </div>
            </div>
        </body>
        </html>
        '''
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending reset email: {str(e)}")
        return False

if __name__ == '__main__':
    with app.app_context():
        # Only create tables if they don't exist (don't drop existing data)
        db.create_all()
        
        # Create default admin only if no admin exists
        admin = User.query.filter_by(username='dhamielectronics').first()
        if not admin:
            admin = User(username='dhamielectronics', email='noreply.dhamielectronics@gmail.com', 
                        password=generate_password_hash('dhamielectronics'), 
                        is_admin=True, is_verified=True)
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin user created!")
        else:
            print("✅ Admin user already exists.")
        
        print("=" * 60)
        print("✅ Database ready!")
        print("👤 Admin credentials - Username: dhamielectronics, Password: dhamielectronics")
        print("📦 Shipping: NPR 150 for orders under NPR 5000")
        print("🚚 Free shipping for orders above NPR 5000")
        print("=" * 60)
    
    print("\n🚀 Starting Flask server...")
    print("🌐 Visit: http://127.0.0.1:5000")
    print("=" * 60)
    
    app.run(debug=True)