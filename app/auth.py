from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from . import login_manager
from .models import User
from typing import Optional

auth_bp = Blueprint("auth", __name__)

# Hard-coded user data (should use database in production)
USERS = {
    "vendor": {
        "password": generate_password_hash("password123"),
        "is_active": True
    }
}

@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    """Load user object"""
    if user_id in USERS:
        return User(user_id)
    return None

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle login request"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        remember = bool(request.form.get("remember"))
        
        if username and password:
            user_data = USERS.get(username)
            if user_data and check_password_hash(user_data["password"], password):
                user = User(username)
                login_user(user, remember=remember)
                # Get the page to redirect to after login
                next_page = request.args.get("next")
                # Ensure next_page is a relative URL (prevent open redirect vulnerability)
                if not next_page or not next_page.startswith("/"):
                    next_page = url_for("upload.upload")
                return redirect(next_page)
        
        flash("Invalid username or password")
        return redirect(url_for("auth.login"))
    
    return render_template("login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    """Handle logout request"""
    logout_user()
    flash("Successfully logged out")
    return redirect(url_for("auth.login"))
