"""
These are common configurations.

1. To connect with MySQL database. 

2. A decorator for checking if "loggedin" in session.

3. function of validation.

"""
from flask import abort, redirect
from flask import url_for
from flask import session
import mysql.connector
from functools import wraps
from mac import connect
import re
from datetime import datetime

db_connection = None


def getCursor():
    """
    Get a new dictionary cursor for the database.

    If you need to open a connection, call this function.

    Example: cursor = getCursor()

    """
    global db_connection

    if db_connection is None or not db_connection.is_connected():
        db_connection = mysql.connector.connect(user=connect.dbuser,
                                                password=connect.dbpass, host=connect.dbhost, auth_plugin='mysql_native_password',
                                                database=connect.dbname, autocommit=True)

    cursor = db_connection.cursor(dictionary=True)

    return cursor


def loginRequired(f):
    """
    """
    @wraps(f)
    def check(*args, **kwargs):
        if not session.get('userData', None):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return check


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def check(*args, **kwargs):
            if not any(role in session.get('userData', {}).get('role', []) for role in roles):
                abort(403)
            return f(*args, **kwargs)
        return check
    return decorator


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowedFile(filename):
    """
    We only accept regular centralized formats, 
    which reduces the risk of display errors

    return:
    true of false

    """

    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def validateUsername(username):
    pattern = r'^[a-zA-Z0-9]{2,20}$'
    if re.match(pattern, username):
        return True
    else:
        return False


def validatePassword(password):
    pattern = r'^[a-zA-Z0-9!@#$%*]{8,20}$'
    if re.match(pattern, password):
        return True
    else:
        return False


def validateEmail(email):
    pattern = r'[^@]+@[^@]+\.[^@]+'
    if re.match(pattern, email):
        return True
    else:
        return False


def validateName(name):
    pattern = r'^[A-Za-z]{2,25}$'
    if re.match(pattern, name):
        return True
    else:
        return False


def validateDate(date):
    try:
        datetime.strptime(date, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validateDateRange(startDate, endDate):
    dateFormat = "%Y-%m-%d"
    try:
        startDate = datetime.strptime(startDate, dateFormat)
        endDate = datetime.strptime(endDate, dateFormat)
        today = datetime.now()
        if startDate < today:
            return False
        if endDate <= startDate:
            return False
        return True
    except ValueError:
        return False


def validateLocation(location):
    pattern = r"^[A-Za-z0-9\s,]{2,50}$"
    if re.match(pattern, location):
        return True
    else:
        return False


# Donation form data validation

def donation_amount(amount):
    """
    Validates if the given amount is a number between 1 and 10,000 (inclusive).
    Returns True if valid, otherwise False.
    """
    try:
        amount = float(amount)
        if 1 <= amount <= 10000:
            return True
        else:
            return False
    except (ValueError, TypeError):
        return False


def validatecardCVV(cardCVV):
    if not cardCVV:
        return False
    pattern = r'^[0-9/\s]{3}$'
    if re.match(pattern, cardCVV):
        return True
    else:
        return False


def validateirdNumber(irdNumber):
    if not irdNumber:
        return False
    pattern = r'^[0-9-\s]{8,11}$'
    if re.match(pattern, irdNumber):
        return True
    else:
        return False


def validateEmpty(value):
    """
    The string cannot be empty or contain only spaces.
    False: is empty or only spaces
    True: something here
    """
    return bool(re.match(r'^(?!\s*$).+', value))
