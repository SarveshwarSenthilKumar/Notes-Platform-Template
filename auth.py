from flask import Flask, render_template, request, redirect, session, jsonify, Blueprint, url_for
from flask_session import Session
from datetime import datetime
import pytz
from sql import *  # Used for database connection and management
from SarvAuth import *  # Used for user authentication functions

auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.route("/login", methods=["GET", "POST"])
def login():
    if session.get("name"):
        return redirect(url_for('dictionary.index'))
        
    if request.method == "GET":
        return render_template("/auth/login.html")
        
    # Handle POST request
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "").strip()

    if not username or not password:
        return render_template("/auth/login.html", error="Username and password are required")
        
    password_hash = hash(password)
    db = SQL("sqlite:///users.db")
    users = db.execute("SELECT * FROM users WHERE username = :username", username=username)

    if not users or users[0]["password"] != password_hash:
        return render_template("/auth/login.html", error="Invalid username or password")
            
    # Successful login
    session["name"] = username
    return redirect(url_for('dictionary.index'))
    
@auth_blueprint.route("/logout")
def logout():
    session["name"] = None
    return redirect("/")
