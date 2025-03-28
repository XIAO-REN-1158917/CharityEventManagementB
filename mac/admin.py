import re
from datetime import datetime
from mac import app
from flask import render_template
from flask import redirect
from flask import url_for
from mac.common import getCursor, validateEmpty, loginRequired, role_required
from flask import render_template
from mac.utils import getApplicationsList
from flask import jsonify, request, session

"""
site admin dashboard page and functions
1. site admin dashboard - connect to dashboard html - launch point for site admin functions
2. see list of competition applications
3. see details view of competition applications
4. approve competition application
5. decline competition application
6. see searchable list of users (similar to admin function from project 1)
7. select and see profile page of user
8. change user status from voter to site admin and vice versa

"""


@app.route('/dashboard')
@loginRequired
def dashboard():
    """
    Renders the site admin dashboard page with site admin specific function links
    Returns:
    render dashboard.html
    """
    msg = session.pop('msg', None)
    return render_template('dashboard.html', msg=msg)


@app.route('/competitionApplicationReview')
@role_required('admin')
def competitionApplicationReview():
    """
    1. fetch all competition submissions with status of 'pending' AND proposer_id does not match logged-in session id  
    2. pass to competitionReviewPage for display
    Returns:
    competitionReviewPage.html
    Note: to be fine-tuned later once log in function operating so have access to session id when testing
    """
    approverId = session.get('userData', {})['user_id']
    pendingCompetitionApplication = getApplicationsList(
        'competition_application', 'pending', approverId)
    pendingDonationApplication = getApplicationsList(
        'donation_application', 'pending', approverId)
    msg = session.pop('msg', None)
    return render_template('competitionApplicationReviewPage.html',
                           pendingCompetitionApplication=pendingCompetitionApplication,
                           pendingDonationApplication=pendingDonationApplication,
                           msg=msg)


@app.route('/competitionApplicationDetail/<int:applicationId>', methods=['GET'])
@role_required('admin')
def competitionApplicationDetail(applicationId):
    """
    1. Receive application_id via GET link
    2. fetch all competition application detail information
    3. pass to competitionReviewDetail for display
    4. competitionReviewDetail will have accept, decline and comment parts for those functions
    Returns:
    competitionReviewDetail.html
    """
    cursor = getCursor()
    sql = """ 
    SELECT user.user_id, user.username, competition_application.application_id, competition_application.theme, competition_application.description, competition_application.create_at, competition_application.status,competition_application.type 
    FROM user 
    RIGHT JOIN competition_application 
    ON user.user_id = competition_application.proposer_id
    WHERE competition_application.application_id = %s; 
    """
    cursor.execute(sql, (applicationId,))
    competitionapplicationDetails: dict = cursor.fetchone()
    msg = session.pop('msg', None)
    return render_template('competitionReviewDetail.html', competitionapplicationDetails=competitionapplicationDetails,msg=msg)


@app.route('/donationApplicationDetail/<int:applicationId>', methods=['GET'])
@role_required('admin')
def donationApplicationDetail(applicationId):
    cursor = getCursor()
    sql = """ 
    SELECT user.user_id, user.username, donation_application.* 
    FROM user 
    RIGHT JOIN donation_application 
    ON user.user_id = donation_application.proposer_id
    WHERE donation_application.application_id = %s; 
    """
    cursor.execute(sql, (applicationId,))
    donationApplicationDetail: dict = cursor.fetchone()
    return render_template('donationReviewDetail.html',
                           donationApplicationDetail=donationApplicationDetail)


@app.route('/approveCompetition', methods=["POST"])
@role_required('admin')
def approveCompetition():
    """
    1. Receive competition proposer id and competition application id
    2. Update competition application status to 'approved'
    3. Insert entry into competition_approval table: application_id, approver_id, set approval_status to 'approved, current timestamp'
    4. Insert entry into competition table: application_id, set message_board to 'closed'
    5. Insert entry into staff table: competition_id(application_id), user_id(proposer_id), add role of 'cadmin' to user_id
    Returns:
    competitionApplicationReviewPage.html
    """

    proposerId = request.form['proposerId']
    applicationId = request.form['applicationId']
    approverId = session.get('userData', {})['user_id']
    cursor = getCursor()
    sql = "UPDATE competition_application SET status = 'approved' WHERE application_id=%s;"
    cursor.execute(sql, (applicationId,))
    sql = '''INSERT INTO competition_approval
            (application_id, approver_id, approval_status, feedback) 
            VALUES (%s, %s, %s, %s);'''
    cursor.execute(sql, (applicationId, approverId,
                         'approved', '',))
    sql = '''INSERT INTO competition
            (application_id)
            VALUES (%s);'''
    cursor.execute(sql, (applicationId,))
    competitionId = cursor.lastrowid
    sql = '''INSERT INTO staff 
            (competition_id,user_id,role)
            VALUES (%s, %s, %s);'''
    cursor.execute(sql, (competitionId, proposerId, 'cadmin'))

    session['msg'] = "Competition Approved!"
    return redirect(url_for('competitionApplicationReview'))


@app.route('/approveDonation', methods=['POST'])
@role_required('admin')
def approveDonation():
    applicationId = request.form['applicationId']
    approverId = session.get('userData', {})['user_id']
    with getCursor() as cursor:
        sql = '''UPDATE donation_application
                SET status = 'approved'
                WHERE application_id = %s;
        '''
        cursor.execute(sql, (applicationId,))
        sql = '''INSERT INTO donation_approval (application_id, approver_id, status, feedback)
                VALUES (%s, %s, 'approved', '');
        '''
        cursor.execute(sql, (applicationId, approverId))
    session['msg'] = "Donation Status Approved!"
    return redirect(url_for('competitionApplicationReview'))


@app.route('/approveDeleteCompetition', methods=["POST"])
@role_required('admin')
def approveDeleteCompetition():
    applicationId = request.form['applicationId']
    approverId = session.get('userData', {})['user_id']
    cursor = getCursor()

    # approve this application
    sql = "UPDATE competition_application SET status = 'approved' WHERE application_id=%s;"
    cursor.execute(sql, (applicationId,))
    # add a record of this approval
    sql = '''INSERT INTO competition_approval
                (application_id, approver_id, approval_status, feedback) 
                VALUES (%s, %s, %s, %s);'''
    cursor.execute(sql, (applicationId, approverId,
                         'approved', '',))
    # fetch the competition_id to delete(archive)
    sql = '''SELECT competition_id_delete
                FROM competition_application
                WHERE application_id = %s;
        '''
    cursor.execute(sql, (applicationId,))
    competitionIdDict = cursor.fetchone()
    competitionId = competitionIdDict['competition_id_delete']
    # delete proposer all staff roles in this competition
    sql = '''DELETE FROM staff
            WHERE competition_id = %s;
    '''
    cursor.execute(sql, (competitionId,))
    # ban all events
    sql = '''UPDATE event
            SET status = 'ban'
            WHERE competition_id = %s;
    
    '''
    # archive this competition, invisible now
    cursor.execute(sql, (competitionId,))
    sql = '''UPDATE competition
            SET status = 'archive'
            WHERE competition_id = %s;
    '''
    cursor.execute(sql, (competitionId,))
    session['msg'] = "Competition Archived!"
    return redirect(url_for('competitionApplicationReview'))


@app.route('/declineCompetition', methods=["POST"])
@role_required('admin')
def declineCompetition():
    """
    1. Receive application_id
    2. Receive feedback
    3. Check feedback filled out. If not return to competitionReviewDetail with message
    4. Update competition application status to 'declined'
    5. Insert entry into competition_approval table: application_id, approver_id, set approval_status to 'declined', feedback, current timestamp'
    Returns:
    competitionApplicationReviewPage.html
    """
    type = request.form['type']
    feedBack = request.form['feedback']
    applicationId = request.form['applicationId']
    if not validateEmpty(feedBack):
        session['msg'] = "Must provide reason for declining application."
        return redirect(url_for('competitionApplicationDetail', applicationId=applicationId))

    approverId = session.get('userData', {})['user_id']
    with getCursor() as cursor:
        if type == 'competition':
            sql = "UPDATE competition_application SET status = 'declined' WHERE application_id=%s;"
            cursor.execute(sql, (applicationId,))
            sql = """
                INSERT INTO competition_approval 
                (application_id, approver_id, approval_status, feedback) 
                VALUES (%s, %s, %s, %s);
            """
            cursor.execute(
                sql, (applicationId, approverId, 'declined', feedBack))
        elif type == 'donation':
            sql = "UPDATE donation_application SET status = 'declined' WHERE application_id=%s;"
            cursor.execute(sql, (applicationId,))
            sql = """
                INSERT INTO donation_approval 
                (application_id, approver_id, status, feedback) 
                VALUES (%s, %s, %s, %s);
            """
            cursor.execute(
                sql, (applicationId, approverId, 'declined', feedBack))

    session['msg'] = "Application Declined!"
    return redirect(url_for('competitionApplicationReview'))


@app.route("/searchUser/", methods=["GET", "POST"])
@role_required('admin', 'cadmin', 'cscrutineer', 'cmoderator')
def searchUser():
    """
    Handle user search and display user management page.

    GET:
    It queries and displays a list of all users, ordered by username, first name, and last name.

    POST:
    1. It processes the search query provided by the user,
    2. trims whitespace from the search input,
    3. performs a case-insensitive and partial match search for users whose username, first name, or last name matches the search query,
    4. displays the search results.

    Render the template, show the results.
    Returns:
    userManagement.html with results shown OR
    userManagement.html with error message (if no matching results)
    """
    cursor = getCursor()
    # If GET, show all users.
    if request.method == "GET":
        source = request.args.get('source')
        cursor.execute(
            "SELECT * FROM user ORDER BY username, first_name, last_name;"
        )
        userList = cursor.fetchall()
        return render_template("searchUser.html", userList=userList, source=source)
    # If POST, show users based on the search results.
    if request.method == "POST":
        name = request.form["name"]
        source = request.args.get('source')
        # Trim space
        name = re.sub(r"\s+", "", name)
        if not name:
            return redirect(url_for("searchUser", source=source))

        sql = """SELECT * 
        FROM user
        WHERE CONCAT(username,first_name,last_name) LIKE %s
        ORDER BY username, first_name, last_name;"""
        # Partial match
        cursor.execute(sql, ("%" + name + "%",))
        userList = cursor.fetchall()
        # If no data matched, send a error message.
        if not userList:
            msg = "No matching results."
            return render_template(
                "searchUser.html", userList=userList, msg=msg
            )
        return render_template("searchUser.html", userList=userList, source=source)


@app.route("/appointSiteRole", methods=["POST"])
@role_required('admin')
def appointSiteRole():
    role = request.form["role"]
    userId = request.form["userId"]
    cursor = getCursor()
    # Only admin has the permission
    cursor.execute(
        "UPDATE user SET role=%s WHERE user_id=%s;", (role, userId))
    # To check the up-to-date status and/or role
    return redirect(url_for("profile", userId=userId))


@app.route('/changeUserStatus', methods=["POST"])
@role_required('admin', 'helper', 'cadmin', 'cscrutineer')
def changeUserStatus():
    status = request.form["status"]
    userId = request.form["userId"]
    source = request.form.get('source')
    cursor = getCursor()
    sql = '''UPDATE user 
            SET status=%s 
            WHERE user_id=%s;
    '''
    cursor.execute(sql, ((status, userId)))
    if source:
        requesterId = request.form['requesterId']
        return redirect(url_for('requesterDetailForHelper', requesterId=requesterId))
    else:
        return redirect(url_for("profile", userId=userId))


@app.route('/competitionManagementForSiteAdmin')
@role_required('admin')
def competitionManagementForSiteAdmin():
    cursor = getCursor()
    sql = '''SELECT c.competition_id AS c_id, c.*, ca.*
            FROM competition AS c
            JOIN competition_application AS ca
            ON c.application_id = ca.application_id
            WHERE c.status = 'open';
    '''
    cursor.execute(sql)
    competitions = cursor.fetchall()
    return render_template('competitionManagementForSiteAdmin.html', competitions=competitions)


@app.route('/globalAnnouncement', methods=["GET", "POST"])
@role_required('admin')
def globalAnnouncement():
    if request.method == 'POST':
        userId = session.get('userData', {})['user_id']
        title = request.form['title']
        content = request.form['content']
        cursor = getCursor()
        sql = '''INSERT INTO `announcement` (announcer_id, title, content, competition_id, type)
                VALUES (%s, %s, %s, NULL, 'global');
        '''
        cursor.execute(sql, (userId, title, content))
        return redirect(url_for('globalAnnouncement'))
    else:
        cursor = getCursor()
        sql = '''SELECT * 
                FROM `announcement` 
                WHERE `type` = 'global' 
                ORDER BY `create_at` DESC;
        '''
        cursor.execute(sql)
        announcements = cursor.fetchall()
        msg = session.pop('msg', None)
        return render_template('globalAnnouncement.html', announcements=announcements)


@app.route('/deleteAnnouncement', methods=["POST"])
@role_required('admin')
def deleteAnnouncement():
    announcementId = request.form['announcementId']
    cursor = getCursor()
    sql = '''DELETE FROM `announcement` 
            WHERE `announcement_id` = %s;
    '''
    cursor.execute(sql, (announcementId,))
    session['msg']="Announcement Deleted!"
    return redirect(url_for('globalAnnouncement'))

@app.route('/allAnnouncements')
def allAnnouncements():
    with getCursor() as cursor:
        # Fetch all announcements
        cursor.execute(
            "SELECT * FROM announcement WHERE type='global' ORDER BY create_at DESC")
        announcements = cursor.fetchall()

        # Render a view-only announcements page
    return render_template('allAnnouncements.html', announcements=announcements)
