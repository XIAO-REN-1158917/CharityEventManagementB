import os
from flask import Flask

"""
Use flask to instantiate an app

Complete the initial configuration, 
including the path and format requirements for uploading files

Check the uploads path if exist.

"""

app = Flask(__name__)

app.secret_key = 'a_secret_key'

# Path (and format) for saving or deleting image file
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS


def check_upload_folder_path(app):
    """
    Ensure the preset file upload path and subdirectories exist. 
    Create them if they do not.
    """
    required_subfolders = ['competitor_images',
                           'profile_images', 'event_images']
    for folder in required_subfolders:
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)


# Perform path checking operations at the initialization stage
check_upload_folder_path(app)

# fmt: off
from mac import voter
from mac import competitionAdmin
from mac import competitionScrutineer
from mac import admin
from mac import helper
from mac import competitionModerator

# fmt: on