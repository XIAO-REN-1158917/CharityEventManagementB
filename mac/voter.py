
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table, TableStyle
from decimal import Decimal
from io import BytesIO
from decimal import Decimal
import os
import re
import json
from mac import app
from flask import current_app
from flask import Response
from flask import send_file
from flask import render_template
from flask import request, session
from flask import redirect
from flask import url_for
from flask_hashing import Hashing
from werkzeug.utils import secure_filename
from mac.utils import getEventsByStatus, getUserRole, getCompetitorsInAnEvent, getMyApplicationList, uploadImage, getCompetitionForStaff
from mac.common import (
    validateEmpty,
    getCursor,
    loginRequired,
    validateUsername,
    validatePassword,
    validateEmail,
    validateName,
    validateDate,
    validateDateRange,
    validateLocation,
    validateEmpty,
    allowedFile,
    donation_amount,
)


hashing = Hashing()
PASSWORD_SALT = 'b29f7d45'
"""
8. announcement detail page
11. message board page
12. send message
13. send reply
18. help center page (request list)
19. send help request
20. sort request
21. request detail page
22. send message in request
23. donation page (recent donator)
24. donate
26. anonymous or not
27. receipt page
28. download PDF
"""


@app.route('/login', methods=['GET', 'POST'])
@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        session['username'] = username
        if not validateEmpty(username) or not validateEmpty(password):
            msg = "Invalid username or password."
            return redirect(url_for('login', msg=msg))
        # Query user account based on username
        cursor = getCursor()
        cursor.execute(
            'SELECT * FROM user WHERE username = %s', (username,))
        # Fetch one record and return result
        account: dict = cursor.fetchone()

        # If account exists in user table
        if account is not None:
            password_hash = account['password_hash']
            if hashing.check_value(password_hash, password, PASSWORD_SALT):
                session.pop('username', '')
                # Create session data, we can access this data in other routes
                # userData is the dict contains all user info
                session['userData'] = account
                # add loggedin key:loggedin value:True
                session['userData']['loggedin'] = True
                roleSet: set = getUserRole(account['user_id'])
                # Set the value of role to all roles that the user has.
                session['userData']['role'] = list(roleSet)
                # If the user has special roles at the competition level,
                # find the competition IDs corresponding to these roles and store them in the session
                if 'cadmin' in session['userData']['role']:
                    cadminList = getCompetitionForStaff(
                        account['user_id'], 'cadmin')
                    session['userData']['cadmin'] = cadminList
                if 'cscrutineer' in session['userData']['role']:
                    cscrutineerList = getCompetitionForStaff(
                        account['user_id'], 'cscrutineer')
                    session['userData']['cscrutineer'] = cscrutineerList
                if 'cmoderator' in session['userData']['role']:
                    cmoderatorList = getCompetitionForStaff(
                        account['user_id'], 'cmoderator')
                    session['userData']['cmoderator'] = cmoderatorList

            else:
                # password incorrect
                msg = 'Incorrect password!'
                return redirect(url_for('login', msg=msg))
        else:
            # Account doesn't exist or username incorrect
            msg = "Account doesn't exist"

        return redirect(url_for('home'))
    elif request.method == "GET":
        msg = request.args.get('msg')
        username = session.get('username', '')
        return render_template('loginPage.html', msg=msg, username=username)


@app.route('/', methods=['GET'])
@app.route('/home', methods=['GET'])
def home():
    allCurrentEvents = getEventsByStatus(None, 'current')
    allFinalEvents = getEventsByStatus(None, 'final')
    with getCursor() as cursor:
        sql = '''SELECT * 
                FROM donation 
                LEFT JOIN donation_application ON donation.competition_id = donation_application.competition_id
                WHERE NOT donation.status = 'ban'
                AND donation_application.status = 'approved';
        '''
        cursor.execute(sql)
        donations = cursor.fetchall()
        sql = '''SELECT * 
                FROM `announcement` 
                WHERE `type` = 'global' 
                ORDER BY `create_at` DESC;
            '''
        cursor.execute(sql)
        announcements = cursor.fetchall()

        sql = '''SELECT event.title,user.username,vote.create_at 
                FROM vote
                LEFT JOIN `user` ON user.user_id=vote.voter_id
                LEFT JOIN candidate ON vote.candidate_id = candidate.candidate_id
                LEFT JOIN `event` ON event.event_id = candidate.event_id
                ORDER BY vote.create_at
                LIMIT 10;
        '''
        cursor.execute(sql)
        recentVotes = cursor.fetchall()

        sql = '''SELECT dr.record_id,u.username,dr.amount,dr.create_at,da.charity_name
                FROM donation_record AS dr
                LEFT JOIN `user` AS u
                ON u.user_id=dr.donor_id
                LEFT JOIN donation_application AS da
                ON dr.donation_id = da.competition_id
                WHERE da.status = 'approved'
                ORDER BY dr.create_at desc
                LIMIT 10;
        '''
        cursor.execute(sql)
        recentDonations = cursor.fetchall()

        sql = '''SELECT SUM(amount) AS total_amount
            FROM donation_record;
        '''
        cursor.execute(sql)
        donationTotalAmountDic = cursor.fetchone()
        donationTotalAmount = donationTotalAmountDic.get('total_amount', None)

        sql = '''SELECT COUNT(*) AS total_records
                FROM donation_record;
        '''
        cursor.execute(sql)
        donationTimesDic = cursor.fetchone()
        donationTimes = donationTimesDic.get('total_records', None)
        sql = '''SELECT SUM(amount) AS total_amount
                FROM donation_record
                WHERE create_at >= NOW() - INTERVAL 30 DAY;
        '''
        cursor.execute(sql)
        lastMonthDonationAmountDic = cursor.fetchone()
        lastMonthDonationAmount = lastMonthDonationAmountDic.get(
            'total_amount', None)

    return render_template('home.html',
                           allCurrentEvents=allCurrentEvents,
                           allFinalEvents=allFinalEvents,
                           announcements=announcements,
                           recentVotes=recentVotes,
                           recentDonations=recentDonations,
                           donations=donations,
                           donationTotalAmount=donationTotalAmount,
                           donationTimes=donationTimes,
                           lastMonthDonationAmount=lastMonthDonationAmount
                           )


@app.route('/competitionDetail/<int:competitionId>', methods=['GET'])
def competitionDetail(competitionId):
    """
    1. Pull competition theme, description, message_board
    2. Pull event details for events with current and final status
    3. Pull current event candidates
    4. Display via template
    Returns:
    homeToCompetitionDetail.html
    """

    session['competition'] = {'competitionId': competitionId}
    currentEvent = getEventsByStatus(competitionId, 'current')
    finalEvents = getEventsByStatus(competitionId, 'final')

    with getCursor() as cursor:
        sql = '''SELECT donation_record.*,user.username 
                FROM donation_record
                LEFT JOIN user ON user.user_id = donation_record.donor_id
                WHERE donation_id = %s
                ORDER BY donation_record.create_at DESC
                LIMIT 10;
        '''
        cursor.execute(sql, (competitionId,))
        donationRecords = cursor.fetchall()
        sql = """ SELECT competition.status, competition_application.theme, competition_application.description
            FROM competition
            RIGHT JOIN competition_application
            ON competition.application_id = competition_application.application_id
            WHERE competition.competition_id=%s;
            """
        cursor.execute(sql, (competitionId,))
        selectedCompetition = cursor.fetchall()

        sql = '''SELECT * 
                    FROM `announcement` 
                    WHERE `competition_id` = %s
                    ORDER BY `create_at` DESC;
            '''
        cursor.execute(sql, (competitionId,))
        announcements = cursor.fetchall()

        sql = '''SELECT d.*, da.*
                FROM donation d
                JOIN donation_application da 
                ON d.competition_id = da.competition_id
                WHERE da.status = 'approved'
                AND da.competition_id = %s
        '''
        cursor.execute(sql, (competitionId,))
        donateButton = cursor.fetchone()

    if not finalEvents:
        msg = "There are no finished events for this competition yet."
        return render_template('homeToCompetitionDetail.html',
                               selectedCompetition=selectedCompetition,
                               currentEvent=currentEvent,
                               announcements=announcements,
                               donateButton=donateButton,
                               donationRecords=donationRecords,
                               finalEvents=None,
                               msg=msg)

    return render_template('homeToCompetitionDetail.html',
                           selectedCompetition=selectedCompetition,
                           currentEvent=currentEvent,
                           finalEvents=finalEvents,
                           announcements=announcements,
                           donateButton=donateButton,
                           donationRecords=donationRecords)


@app.route('/currentEventDetail/<int:eventId>', methods=['GET'])
def currentEventDetail(eventId):
    cursor = getCursor()
    sql = '''SELECT 
                user.user_id,
                user.public,
                user.username,
                user.description,
                user.profile_image
            FROM 
                user
            JOIN 
                vote ON user.user_id = vote.voter_id
            JOIN 
                candidate ON vote.candidate_id = candidate.candidate_id
            WHERE 
                candidate.event_id = %s
            ORDER BY 
                vote.create_at DESC
            LIMIT 10;
    
    '''
    cursor.execute(sql, (eventId,))
    recentTenVoteRecords = cursor.fetchall()

    sql = '''SELECT *
                FROM event
                WHERE event_id = %s;
        '''
    cursor.execute(sql, (eventId,))
    eventInfo: dict = cursor.fetchone()
    session['event'] = eventInfo
    competitors: list[dict] = getCompetitorsInAnEvent(eventId)
    voterId = session.get('userData', {}).get('user_id', None)
    if voterId:
        cursor = getCursor()
        sql = '''SELECT 1
                FROM vote
                JOIN candidate ON vote.candidate_id = candidate.candidate_id
                WHERE vote.voter_id = %s AND candidate.event_id = %s
                LIMIT 1;
        '''
        cursor.execute(sql, (voterId, eventId))
        checkIfVoted = cursor.fetchone()
        msg = session.pop('msg', None)
        return render_template('currentEventDetailPage.html',
                               eventInfo=eventInfo,
                               competitors=competitors,
                               checkIfVoted=checkIfVoted,
                               recentTenVoteRecords=recentTenVoteRecords,
                               msg=msg)
    else:
        msg = session.pop('msg', None)
        return render_template('currentEventDetailPage.html',
                               eventInfo=eventInfo,
                               competitors=competitors,
                               recentTenVoteRecords=recentTenVoteRecords,
                               msg=msg)


@app.route('/finalEventDetail/', methods=['GET'])
def finalEventDetail():
    '''
    1. Receive eventId from homeToCompetitionDetail.html
    2. Pull event data using eventId
    3. Pull candidate data for eventId and format as list of dictionary entries
    4. Pull winning competitor data from result table for eventId
    5. Calculate total votes and vote % for each candidate with match eventId (ignoring NULL votes)
    6. Pass to template for display

    '''
    eventId = request.args.get('eventId', None)
    cursor = getCursor()
    sql = '''SELECT *
                FROM event
                WHERE event_id = %s;
        '''
    cursor.execute(sql, (eventId,))
    eventInfo: dict = cursor.fetchall()
    session['event'] = eventInfo
    competitors: list[dict] = getCompetitorsInAnEvent(eventId)

    sql = """
            SELECT competitor.name,
            competitor.description,
            competitor.image,
            result.total_votes,
            result.percentage
            FROM competitor
            INNER JOIN candidate AS candidate
            ON competitor.competitor_id = candidate.competitor_id
            INNER JOIN result AS result
            ON candidate.candidate_id = result.candidate_id
            WHERE candidate.event_id = %s;
            """
    cursor.execute(sql, (eventId,))
    winningCompetitorResult = cursor.fetchall()

    competitionId = eventInfo[0]['competition_id']

    sql = """
            WITH total_votes AS (
            SELECT SUM(vote_count) AS total_votes
            FROM (
            SELECT COUNT(vote.vote_id) AS vote_count
            FROM vote
            RIGHT JOIN candidate
            ON vote.candidate_id = candidate.candidate_id
            WHERE candidate.competition_id = %s
            AND candidate.event_id = %s
            AND vote.vote_id IS NOT NULL
            AND vote.status = 'valid'
            GROUP BY candidate.candidate_id
            ) AS vote_counts
            )
            SELECT subquery.candidate_id, 
            subquery.competitor_id, 
            COUNT(subquery.vote_id) AS vote_count, 
            (COUNT(subquery.vote_id) / total_votes.total_votes) * 100 AS percentage
            FROM (
            SELECT vote.vote_id, 
            candidate.candidate_id, 
            candidate.competitor_id
            FROM vote
            RIGHT JOIN candidate
            ON vote.candidate_id = candidate.candidate_id
            WHERE candidate.event_id = %s
            AND vote.vote_id IS NOT NULL
            AND vote.status = 'valid'
            ) AS subquery
            CROSS JOIN total_votes
            GROUP BY subquery.candidate_id, subquery.competitor_id, total_votes.total_votes;
            """
    cursor.execute(sql, (competitionId, eventId, eventId))
    allCompetitorVoteDetail = cursor.fetchall()

    return render_template('finalEventDetail.html',
                           eventInfo=eventInfo,
                           competitors=competitors,
                           winningCompetitorResult=winningCompetitorResult,
                           allCompetitorVoteDetail=allCompetitorVoteDetail
                           )


@app.route('/applyCompetition', methods=['GET', 'POST'])
@loginRequired
def applyCompetition():
    if request.method == "POST":
        theme = request.form['theme']
        description = request.form['description']
        proposerId = session.get('userData', {})['user_id']
        if not theme or not description:
            session['msg'] = 'Please input both theme and description.'
            return redirect(url_for('applyCompetition'))
        cursor = getCursor()
        sql = '''INSERT INTO competition_application (proposer_id,theme, description)
                VALUES (%s,%s, %s);
        '''
        cursor.execute(sql, (proposerId, theme, description,))
        session['msg'] = 'Submission successful, awaiting approval...'
        return redirect(url_for('myApplication'))
    elif request.method == "GET":
        msg = session.pop('msg', None)
        return render_template('applyCompetition.html', msg=msg)


@app.route('/myApplication', methods=['GET'])
@loginRequired
def myApplication():
    userId = session.get('userData', {})['user_id']
    myCompetitionApplication = getMyApplicationList(
        'competition_application', None, userId)
    myDonationApplication = getMyApplicationList(
        'donation_application', None, userId)
    msg = session.pop('msg', None)
    return render_template('myApplication.html',
                           myCompetitionApplication=myCompetitionApplication,
                           myDonationApplication=myDonationApplication,
                           msg=msg)


@app.route('/deleteApplication', methods=['POST'])
@loginRequired
def deleteApplication():
    """
    1. Receive application_id from form post
    2. Delete record from competition_application table and competition_approval table where application_id == received
    3. Returns to same page with record removed from user view
    Returns:
    myApplication.html
    """
    applicationId = request.form.get('applicationId')
    type = request.form.get('type')

    cursor = getCursor()
    if type == 'competition' or type is None:
        sql = "DELETE FROM competition_approval WHERE application_id=%s"
        cursor.execute(sql, (applicationId,))
        sql = "DELETE FROM competition_application WHERE application_id=%s;"
        cursor.execute(sql, (applicationId,))
        session['msg'] = "Application deletion successful"
    elif type == 'donation':
        sql = "DELETE FROM donation_approval WHERE application_id=%s"
        cursor.execute(sql, (applicationId,))
        sql = "DELETE FROM donation_application WHERE application_id=%s"
        cursor.execute(sql, (applicationId,))
        session['msg'] = "Application deletion successful"
    else:
        return render_template('404.html')
    return redirect(url_for('myApplication'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return render_template('404.html'), 405


@app.errorhandler(403)
def forbidden(error):
    return render_template('403.html'), 403


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    POST
    1. Verify that the username is not duplicated.
    2. Perform validation on the back end in case the front end form validation is bypassed.
    3. Add the new authenticated user to the database.
    GET
    1. Render template - register.html
    Returns:
        Username is duplicated or Failed verification: Prompt error message and re-register
        Successful register: Add the new user to the database and re-login
    """
    if request.method == 'POST':
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        confirmPassword = request.form['confirmPassword']
        email = request.form['email']
        firstName = request.form['firstname']
        lastName = request.form['lastname']
        location = request.form['location']
        description = request.form['description']
        # Check if account exists using MySQL
        cursor = getCursor()
        cursor.execute(
            'SELECT user_id FROM user WHERE username = %s OR email=%s', (username, email))
        account = cursor.fetchone()

        # If username exists show error and validation checks
        if account:
            session['msg'] = 'The username or email already exists, please try again.'
        elif not validateUsername(username):
            session['msg'] = "Please enter a username consisting of 2 to 20 characters and numbers."
        elif not validatePassword(password):
            session[
                'msg'] = "Please enter a password consisting of 8 to 20 characters and numbers and at least one special symbol (special symbols: !@#$%*)."
        elif password != confirmPassword:
            session['msg'] = "The passwords you enter twice should match."
        elif not validateEmail(email):
            session['msg'] = "Invalid email address!"
        elif not validateName(firstName):
            session['msg'] = "Please enter 2-50 English letters as your first-name."
        elif not validateName(lastName):
            session['msg'] = "Please enter 2-50 English letters as your last-name."
        elif not validateLocation(location):
            session['msg'] = "Address should be 2-50 characters long and can include letters, numbers, spaces and commas."
        # elif not validateDescription(description):
        #     msg = "Address should be 2-255 characters long and can include letters, numbers, spaces and commas."
        else:
            # Account doesn't exist and the form data is valid, now insert new account into users table
            password_hash = hashing.hash_value(password, PASSWORD_SALT)
            cursor.execute('INSERT INTO user (username, password_hash, email, first_name, last_name, location, description) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                           (username, password_hash, email, firstName, lastName, location, description))
            # To prompt user with a successful message
            msg = 'You have successfully registered! Please login.'
            # New user should login
            return redirect(url_for('logout', msg=msg))
        # If any errors occur, return to the registration page and display an appropriate message
        msg = session.pop('msg', None)
        return render_template('register.html', msg=msg)
    else:
        return render_template('register.html')


@app.route('/logout/')
def logout():
    """
    Log the user out by clearing the session data and redirecting them to the login page.
    """
    session.clear()
    msg = request.args.get('msg')
    response = redirect(url_for('login', msg=msg))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    # Redirect to login page
    return response


@app.route('/castVote/<int:candidateId>', methods=['GET'])
@loginRequired
def castVote(candidateId):
    eventId = session['event'].get('event_id')
    voterId = session['userData'].get('user_id')
    ipAddress = request.remote_addr
    cursor = getCursor()
    sql = '''INSERT INTO vote (voter_id,candidate_id,ip_address)
            VALUES (%s,%s,%s);
    '''
    cursor.execute(sql, (voterId, candidateId, ipAddress))
    session['msg'] = 'Vote successful! Thank you for voting!'
    return redirect(url_for('currentEventDetail', eventId=eventId))


@app.route('/profile/', methods=['GET', 'POST'])
@loginRequired
def profile():
    if request.method == 'GET':
        userId = request.args.get('userId')
        msg = session.pop('msg', None)
        cursor = getCursor()
        if userId:
            cursor.execute(
                'SELECT * FROM user WHERE user_id = %s', (userId,))
        else:
            cursor.execute(
                'SELECT * FROM user WHERE user_id = %s', (session['userData']['user_id'],))
        user = cursor.fetchone()
        return render_template('profile.html', user=user, msg=msg)

    if request.method == 'POST':
        userId = session.get('userData', {})['user_id']
        if 'profile_image' in request.files:
            uploadFilename = uploadImage('profile_image', 'profile_images')
            if uploadFilename:
                cursor = getCursor()
                cursor.execute(
                    'UPDATE users SET profile_image = %s WHERE user_id = %s', (uploadFilename, session['id']))
                session['userData']['profile_image'] = uploadFilename
            else:
                return redirect(url_for('profile'))
        email = request.form['email']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        description = request.form['description']
        location = request.form['location']
        cursor = getCursor()
        cursor.execute(
            'SELECT user_id FROM users WHERE email=%s AND user_id!=%s', (email, userId))
        account = cursor.fetchone()
        if account:
            msg = 'The email already exists, please try again.'
        elif not validateEmail(email):
            msg = "Invalid email address!"
        elif not validateName(first_name):
            msg = "Please enter 2-50 English letters as your first-name."
        elif not validateName(last_name):
            msg = "Please enter 2-50 English letters as your last-name."
        elif not validateLocation(location):
            msg = "Address should be 2-50 characters long and can include letters, numbers, spaces and commas."
        else:
            cursor = getCursor()
            cursor.execute('UPDATE users SET email = %s, first_name = %s, last_name = %s, description = %s, location = %s WHERE user_id = %s',
                           (email, first_name, last_name, description, location, userId))
            msg = 'Profile updated successfully!'
        session['msg'] = {'msg': msg}
        return redirect(url_for('profile'))


@app.route('/deleteProfileImage', methods=['POST'])
@loginRequired
def deleteProfileImage():
    """
   Deletes the profile image of the current user.

   This function handles the deletion of the user's profile image:
   - Sets the `profile_image` field to `NULL` in the database for the current user.
   - Clears the profile image session variable.
   - Commits the transaction to ensure the change is saved.

   Redirects the user to the home page with a success message.

   Returns:
   - Redirects to the 'home' page with a message indicating that the profile image was deleted successfully.

   """
    cursor = getCursor()
    cursor.execute(
        'UPDATE users SET profile_image = NULL WHERE user_id = %s', (session['userData']['user_id'],))
    session['userData']['profile_image'] = None
    msg = 'Profile image deleted successfully!'
    session['msg'] = {'msg': msg}

    return redirect(url_for('profile'))


@app.route('/updatePassword', methods=['GET', 'POST'])
@loginRequired
def updatePassword():
    """
    Updates the password for the current user.

    Handles the password update process:
    - Validates the old password against the stored hash.
    - Checks if the new password and confirmation match.
    - Ensures the new password is different from the old password.
    - Validates the new password format.

    If all validations pass:
    - Hashes the new password.
    - Updates the password hash in the database.
    - Commits the transaction.

    Redirects the user to the profile page with a message indicating the result of the update operation.

    Returns:
    - Redirects to the 'profile' page with a success or error message.
    """
    if request.method == 'POST':
        old_password = request.form['old_password']
        old_password_hash = hashing.hash_value(old_password, PASSWORD_SALT)
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        cursor = getCursor()
        cursor.execute(
            'SELECT password_hash FROM users WHERE user_id = %s', (session['id'],))
        user = cursor.fetchone()
        if user['password_hash'] != old_password_hash:
            msg = 'Old password is incorrect!'
        elif new_password != confirm_password:
            msg = 'New passwords do not match!'
        elif old_password == new_password:
            msg = 'New password cannot be the same as the old password!'
        elif not validatePassword(new_password):
            msg = "A password consisting of 8 to 20 characters, numbers and at least one special symbol (special symbols: !@#$%*)"
        else:
            # Hash the new password and update it in the database.
            password_hash = hashing.hash_value(new_password, PASSWORD_SALT)
            cursor.execute(
                'UPDATE users SET password_hash = %s WHERE user_id = %s', (password_hash, session['id']))
            msg = 'Password updated successfully!',
            return redirect(url_for('profile', msg=msg))
        return redirect(url_for('profile', msg=msg))


@app.route('/changePublicStatus', methods=["POST"])
@loginRequired
def changePublicStatus():
    public = request.form["public"]
    userId = request.form["userId"]
    cursor = getCursor()
    sql = '''UPDATE user 
            SET public=%s 
            WHERE user_id=%s;
    '''
    cursor.execute(sql, ((public, userId)))
    return redirect(url_for("profile", userId=userId))


@app.route('/messageBoard', methods=['GET', 'POST'])
@loginRequired
def messageBoard():
    competitionId = session.get('competition', {})['competitionId']
    userId = session.get('userData', {})['user_id']
    cursor = getCursor()

    sql = ''' SELECT competition.competition_id, competition.status, competition_application.theme, competition_application.description
            FROM competition
            RIGHT JOIN competition_application
            ON competition.application_id = competition_application.application_id
            WHERE competition.competition_id=%s;
    '''
    cursor.execute(sql, (competitionId,))
    competitionDetail = cursor.fetchone()

    sql = '''
        SELECT message_id
        FROM user_like_msg
        WHERE user_id = %s;
    '''
    cursor.execute(sql, (userId,))
    messageIds = cursor.fetchall()
    messageIdSet = [row['message_id'] for row in messageIds]

    if request.method == 'GET':
        sql = '''SELECT u.user_id, u.username, u.profile_image, u.public, m.*, 
                (SELECT count(1) FROM reply WHERE message_id=m.message_id) AS replyCount
                FROM message m
                JOIN user u ON m.sender_id = u.user_id
                WHERE m.competition_id = %s
                ORDER BY m.create_at DESC;
        '''
        cursor.execute(sql, (competitionId,))
        messageList = cursor.fetchall()

    else:
        search = request.form['search']
        search = re.sub(r"\s+", "", search)
        if not search:
            return redirect(url_for('messageBoard'))
        sql = '''SELECT u.user_id, u.username, u.profile_image, u.public, m.*
                FROM message m
                JOIN user u ON m.sender_id = u.user_id
                WHERE m.competition_id = %s
                AND CONCAT(m.title, u.username) LIKE %s
                ORDER BY m.create_at DESC;
            '''
        search_pattern = f"%{search}%"
        cursor.execute(sql,  (competitionId, search_pattern,))
        messageList = cursor.fetchall()

    sql = '''SELECT u.user_id, u.username, u.profile_image, u.public, r.*
            FROM reply r
            JOIN user u ON r.sender_id = u.user_id
            JOIN message m ON r.message_id = m.message_id
            WHERE m.competition_id = %s
            ORDER BY r.create_at DESC;
    '''
    cursor.execute(sql, (competitionId,))
    replyList = cursor.fetchall()
    return render_template('messageBoard.html',
                           messageList=json.dumps(messageList, default=str),
                           replyList=json.dumps(replyList, default=str),
                           #    competitionStatus=competitionStatus,
                           messageIdSet=json.dumps(messageIdSet, default=str),
                           competitionDetail=json.dumps(competitionDetail, default=str))


@app.route('/sendMessage', methods=['POST'])
@loginRequired
def sendMessage():
    senderId = session.get('userData', {})['user_id']
    competitionId = session.get('competition', {})['competitionId']
    title = request.form['title']
    content = request.form['content']
    cursor = getCursor()
    sql = '''INSERT INTO message (sender_id, competition_id, title, content)
            VALUES (%s, %s, %s, %s);
    '''
    cursor.execute(sql, (senderId, competitionId, title, content))
    return redirect('messageBoard')


@app.route('/sendReply', methods=['POST'])
@loginRequired
def sendReply():
    senderId = session.get('userData', {})['user_id']
    payload = request.get_json()
    messageId = payload['messageId']
    content = payload['content']
    cursor = getCursor()
    sql = '''INSERT INTO reply (sender_id, message_id, content)
            VALUES (%s, %s, %s);
    '''
    cursor.execute(sql, (senderId, messageId, content))

    cursor.execute("SELECT * FROM reply WHERE reply_id = LAST_INSERT_ID()")
    inserted_data = cursor.fetchone()

    sql = '''SELECT u.user_id, u.username, u.profile_image, u.public, r.*
            FROM reply r
            JOIN user u ON r.sender_id = u.user_id           
            WHERE r.reply_id = %s;
          '''
    cursor.execute(sql, (inserted_data['reply_id'],))
    theReply = cursor.fetchone()

    return json.dumps(theReply, default=str)


@app.route('/likeMessage', methods=['POST'])
@loginRequired
def likeMessage():

    payload = request.get_json()
    messageId = payload['messageId']
    print(messageId)
    userId = session.get('userData', {})['user_id']
    cursor = getCursor()
    sql = '''
        UPDATE message
        SET `like` = `like` + 1
        WHERE message_id = %s;
    '''
    cursor.execute(sql, (messageId,))

    sql = '''
        INSERT INTO user_like_msg (message_id, user_id)
        VALUES (%s, %s);
        '''
    cursor.execute(sql, (messageId, userId))

    return {}


@app.route('/myMessage')
@loginRequired
def myMessage():
    userId = session.get('userData', {})['user_id']

    cursor = getCursor()
    sql = '''SELECT * 
            FROM message 
            WHERE sender_id = %s;
    '''
    cursor.execute(sql, (userId,))
    myMessages = cursor.fetchall()

    sql = '''SELECT * 
            FROM reply 
            WHERE sender_id = %s;
    '''
    cursor.execute(sql, (userId,))
    myReplies = cursor.fetchall()

    return render_template('myMessage.html',
                           messages=myMessages,
                           replies=myReplies)


@app.route('/announcementDetail/<int:announcementId>')
def announcementDetail(announcementId):
    cursor = getCursor()
    sql = '''SELECT * 
            FROM `announcement` 
            WHERE `announcement_id` = %s;
    '''
    cursor.execute(sql, (announcementId,))
    announcement = cursor.fetchone()
    return render_template('announcementDetail.html', announcement=announcement)


@app.route('/helpCenterRequester', methods=['GET', 'POST'])
@loginRequired
def helpCenterRequester():
    '''
    '''
    userId = session.get('userData', {}).get('user_id')
    print(userId)
    if request.method == 'POST':
        type = request.form['type']
        if type == 'post':
            title = request.form['title']
            description = request.form['description']
            with getCursor() as cursor:
                sql = '''INSERT INTO request (proposer_id, title, description)
                                VALUES (%s, %s, %s);'''
                cursor.execute(sql, (userId, title, description))
            return redirect(url_for('helpCenterRequester'))
        elif type == 'search':
            search = request.form['search']
            search = re.sub(r"\s+", "", search)
            if not search:
                return redirect(url_for('helpCenterRequester'))
            with getCursor() as cursor:
                sql = '''SELECT * 
                        FROM request 
                        WHERE proposer_id = %s 
                        AND title LIKE %s
                        ORDER BY create_at DESC;
                '''
                search_pattern = f"%{search}%"
                cursor.execute(sql, (userId, search_pattern))
                requests = cursor.fetchall()
            return render_template('helpCenterRequester.html', requests=requests)
    else:
        with getCursor() as cursor:
            sql = '''
                SELECT * 
                FROM request 
                WHERE proposer_id = %s
                ORDER BY create_at DESC;
            '''
            cursor.execute(sql, (userId,))
            requests = cursor.fetchall()
        return render_template('helpCenterRequester.html', requests=requests)


@app.route('/requestDetail/<int:requestId>')
@loginRequired
def requestDetail(requestId):
    source = request.args.get('source')
    with getCursor() as cursor:
        sql = '''SELECT request.request_id AS request_request_id, 
                        request.create_at AS request_create_at,
                        request.*, 
                        request_message.*, 
                        request_user.username AS request_username,
                        request_user.profile_image AS request_profile_image,
                        message_user.username AS message_username
                    FROM request
                    LEFT JOIN request_message ON request.request_id = request_message.request_id
                    LEFT JOIN user AS request_user ON request.proposer_id = request_user.user_id
                    LEFT JOIN user AS message_user ON request_message.sender_id = message_user.user_id
                    WHERE request.request_id = %s
                    ORDER BY request_message.create_at;
            '''
        cursor.execute(sql, (requestId,))
        requestDetail = cursor.fetchall()

        query_helpers = """
        SELECT helper_id 
        FROM customer_service 
        WHERE status = 'open';
        """
        cursor.execute(query_helpers)
        helper_results = cursor.fetchall()

        # Extract helper IDs from the results
        helper_ids = [row['helper_id'] for row in helper_results]

        if helper_ids:
            placeholders = ','.join(['%s'] * len(helper_ids))
            query_users = f"""
                SELECT *
                FROM user
                WHERE role IN ('admin', 'helper')
                AND user_id NOT IN ({placeholders});
            """
            cursor.execute(query_users, tuple(helper_ids))
        else:
            # If no helper IDs, just select all admin and helper roles
            query_users = """
                SELECT * 
                FROM user 
                WHERE role IN ('admin', 'helper');
            """
            cursor.execute(query_users)

        availableHelper = cursor.fetchall()

    return render_template('requestDetail.html',
                           requestDetail=requestDetail,
                           source=source,
                           availableHelper=availableHelper)


@app.route('/sendRequestMessage', methods=['POST'])
@loginRequired
def sendRequestMessage():
    requestId = request.form['requestId']
    senderId = session.get('userData', {}).get('user_id')
    content = request.form['content']
    with getCursor() as cursor:
        sql = '''INSERT INTO request_message (sender_id, request_id, content) 
                VALUES (%s, %s, %s);
        '''
        cursor.execute(sql, (senderId, requestId, content))
    return redirect(url_for('requestDetail', requestId=requestId))

# --------- DONATION SECTION -----------------------------


@app.route('/donationForm', methods=['GET', 'POST'])
@loginRequired
def donationForm():
    competitionId = session.get('competition', {}).get('competitionId', None)
    if request.method == 'GET':
        with getCursor() as cursor:
            sql = '''SELECT d.*, da.*
                    FROM donation d
                    JOIN donation_application da 
                    ON d.donation_id = da.competition_id
                    WHERE da.status = 'approved'
                    AND da.competition_id = %s

            '''
            cursor.execute(sql, (competitionId,))
            donationDetails = cursor.fetchone()
        msg = session.pop('msg', None)
        return render_template('donationForm.html', donationDetails=donationDetails, msg=msg)

    else:
        donateAmount = request.form.get('donateAmount')

        if not donateAmount or not donation_amount(donateAmount):
            session['msg'] = "Please enter an amount to donate between $1 and $10 000."
            return redirect(url_for('donationForm'))

        anonDonate = request.form.get('anonDonate', 'no')
        paymentMethod = request.form.get('paymentMethod')
        if paymentMethod == 'credit':
            return render_template('pay_by_card.html', donateAmount=donateAmount, anonDonate=anonDonate)
        elif paymentMethod == 'transfer':
            return render_template('pay_by_transfer.html', donateAmount=donateAmount, anonDonate=anonDonate)


@app.route('/processingPayment', methods=['POST'])
@loginRequired
def processingPayment():
    payType = request.form['type']
    userId = session.get('userData', {}).get('user_id')
    competitionId = session.get('competition', {}).get('competitionId', None)
    amount = request.form['donateAmount']
    anonymous = request.form['anonDonate']
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with getCursor() as cursor:
        sql = '''INSERT INTO donation_record (donation_id, donor_id, amount, anonymous, create_at) 
        VALUES (%s, %s, %s, %s, %s);
        '''
        print(f"SQL: {sql}")
        print(f"Timestamp: {timestamp}")
        cursor.execute(sql, (competitionId, userId,
                       amount, anonymous, timestamp))

        sql = '''SELECT total_raised, percentage 
                FROM donation 
                WHERE competition_id = %s;
        
        '''
        cursor.execute(sql, (competitionId,))
        result = cursor.fetchone()
        if result:
            amount = Decimal(amount)
            total_raised = result['total_raised']
            percentage = result['percentage']
            new_percentage = (total_raised + amount) / \
                (total_raised / percentage)
            new_total_raised = total_raised + amount
            update_query = """
            UPDATE donation 
            SET percentage = %s, total_raised = %s 
            WHERE competition_id = %s;
            """
            cursor.execute(update_query, (new_percentage,
                           new_total_raised, competitionId))
        else:
            return redirect('donationForm')

        if payType == 'card':
            cardNumber = request.form['cardNumber']
            cardholder = request.form['cardholder']
            cardExpiry = request.form['cardExpiry']
            cardCVV = request.form['cardCVV']
            sql = '''INSERT INTO payment (payment_method, payment_amount, payment_status) 
                VALUES ('card', %s, 'successful');
        '''
            cursor.execute(sql, (amount,))
            paymentId = cursor.lastrowid

            sql = '''INSERT INTO pay_card (payment_id, card_number, expires, cvv, cardholder) 
                    VALUES (%s, %s, %s, %s, %s);
            '''
            cursor.execute(sql, (paymentId, cardNumber,
                           cardExpiry, cardCVV, cardholder))
            session['msg'] = f"Thank you for your donation! View full donation details below. A copy of your tax receipt has been emailed to: {userEmail}."
        elif payType == 'transfer':
            sql = '''INSERT INTO payment (payment_method, payment_amount, payment_status)
                VALUES ('transfer', %s, 'successful');
        '''
            cursor.execute(sql, (amount,))
            paymentId = cursor.lastrowid

            payee = request.form['payee']
            account = request.form['account']
            sql = '''INSERT INTO pay_transfer (payment_id, payee, account_number) 
                    VALUES (%s, %s, %s);
            '''
            cursor.execute(sql, (paymentId, payee, account))
            userEmail = session.get('userData', {}).get('email')
            session['msg'] = f"Thank you for your donation! View full donation details below. A copy of your tax receipt has been emailed to: {userEmail}."
        return redirect('donationHistory')


@app.route('/donationHistory', methods=['GET', 'POST'])
@loginRequired
def donationHistory():
    userId = session.get('userData', {}).get('user_id')
    cursor = getCursor()
    sql = '''
                SELECT dr.*, d.*, d.status AS donation_status, da.*, dr.create_at AS donation_date
                FROM donation_record dr
                JOIN donation d ON dr.donation_id = d.donation_id
                JOIN donation_application da ON d.competition_id = da.competition_id
                WHERE dr.donor_id = %s AND da.status = 'approved'
            '''
    cursor.execute(sql, (userId,))
    pastDonations = cursor.fetchall()
    msg = session.pop('msg', None)
    return render_template('donationHistory.html', pastDonations=pastDonations, msg=msg)


@app.route('/sendReceipt')
@loginRequired
def sendReceipt():
    userEmail = session.get('userData', {}).get('email')
    session['msg'] = f"Please check you email. A copy of the donation receipt has been sent to: {userEmail}"
    return redirect(url_for('donationHistory'))


@app.route('/myDonationReceipt/<int:recordId>')
@loginRequired
def myDonationReceipt(recordId):
    session['recordId'] = recordId

    with getCursor() as cursor:
        sql = '''
                SELECT dr.record_id, dr.donation_id, dr.donor_id, dr.amount, dr.create_at, da.charity_name, da.charity_id, da.ird 
                FROM donation_record dr
                JOIN donation d ON dr.donation_id = d.donation_id
                JOIN donation_application da ON d.competition_id = da.competition_id
                WHERE dr.record_id = %s AND da.status = 'approved';
            '''
        cursor.execute(sql, (recordId,))
        donationDetails = cursor.fetchone()

        return render_template('my_donation_receipt.html', donationDetails=donationDetails)


@app.route('/generatePDF', methods=['GET', 'POST'])
@loginRequired
def generatePDF():
    pdf_file = generatePDFFile()
    return send_file(pdf_file, as_attachment=True, download_name='donationreceipt.pdf')


def generatePDFFile():
    recordIdValue = session.get('recordId')
    with getCursor() as cursor:
        sql = '''
                SELECT dr.record_id, dr.donation_id, dr.donor_id, dr.amount, dr.create_at, da.charity_name, da.charity_id, da.ird 
                FROM donation_record dr
                JOIN donation d ON dr.donation_id = d.donation_id
                JOIN donation_application da ON d.competition_id = da.competition_id
                WHERE dr.record_id = %s AND da.status = 'approved';
            '''
        cursor.execute(sql, (recordIdValue,))
        donationDetails = cursor.fetchone()

    buffer = BytesIO()
    documentTitle = 'donationreceipt'
    title = 'Donation Receipt'
    subTitle = 'Thank you for your donation!'
    receiptDetails = donationDetails
    image = os.path.join(current_app.root_path, 'static', 'images', 'team_logo.png')

    pdf = canvas.Canvas(buffer)
    pdf.setTitle(documentTitle)
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawCentredString(300, 770, title)

    pdf.setFont("Helvetica", 18)
    pdf.drawCentredString(300, 740, subTitle)

    pdf.setStrokeColor(colors.HexColor("0x008000"))
    pdf.setLineWidth(1.5)
    pdf.line(40, 730, 550, 730)

    pdf.setFont("Helvetica", 14)
    pdf.drawString(40, 690, f"Receipt Number: {receiptDetails['record_id']}")
    pdf.drawString(40, 670, f"Issued by:")
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, 650, f"Charity Name: {receiptDetails['charity_name']}")
    pdf.setFont("Helvetica", 14)
    pdf.drawString(40, 630, f"Charity Services Registration Number: {receiptDetails['charity_id']}")
    pdf.drawString(40, 610, f"Charity IRD number: {receiptDetails['ird']}")

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, 560, f"Donor:")
    pdf.setFont("Helvetica", 14)
    pdf.drawString(40, 540, f"Name: {session.get('userData', {}).get('first_name')}, {session.get('userData', {}).get('last_name')}")
    pdf.drawString(40, 520, f"Email: {session.get('userData', {}).get('email')}")

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, 490, f"Donation Details:")
    pdf.setFont("Helvetica", 14)
    pdf.drawString(40, 470, f"Date of Donation: {receiptDetails['create_at'].strftime('%d-%m-%Y')}")
    pdf.drawString(40, 450, f"Amount donated: ${receiptDetails['amount']}")

    data = [
        ["Receipt Number:", receiptDetails['record_id']],
        ["Charity Name:", receiptDetails['charity_name']],
        ["Registration Number:", receiptDetails['charity_id']],
        ["IRD Number:", receiptDetails['ird']],
        ["Donor Name:", f"{session.get('userData', {}).get('first_name')}, {session.get('userData', {}).get('last_name')}"],
        ["Email:", f"{session.get('userData', {}).get('email')}"],
        ["Date of Donation:",receiptDetails['create_at'].strftime('%d-%m-%Y')],
        ["Amount Donated:", f"${receiptDetails['amount']}"]
    ]

    table = Table(data, colWidths=[160, 300])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("0xF8F8FF")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))

    table.wrapOn(pdf, 450, 200)
    table.drawOn(pdf, 40, 200)

    pdf.setLineWidth(1)
    pdf.line(40, 150, 550, 150)

    pdf.setFont("Helvetica", 12)
    pdf.drawString(40, 60, f"Authorised by Make A Change General Manager: D.A.BOSS")
    pdf.drawInlineImage(image, 400, 60, width=80, height=80)

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return buffer
