from mac import app
import uuid
import os
from mac.common import getCursor, validateDateRange, role_required
from mac.utils import getEventsByStatus, getCompetitorsInAnEvent, getMyApplicationList, uploadImage
from flask import jsonify, request, session
from flask import render_template
from flask import redirect
from flask import url_for
from werkzeug.utils import secure_filename


@app.route('/competitionManagement')
@role_required('cadmin')
def competitionManagement():
    cursor = getCursor()
    proposerId = session.get('userData', {})['user_id']
    sql = '''SELECT competition_id
            FROM staff
            WHERE user_id = %s
            AND role = 'cadmin';
    '''
    cursor.execute(sql, (proposerId,))
    competitions = []

    competitionIds = cursor.fetchall()
    for competitionIdDict in competitionIds:
        competitionId = competitionIdDict['competition_id']
        sql = '''SELECT c.competition_id, ca.theme
                FROM competition AS c
                LEFT JOIN competition_application AS ca
                ON c.application_id = ca.application_id
                WHERE c.competition_id = %s;
        '''
        cursor.execute(sql, (competitionId,))
        competition: dict = cursor.fetchone()
        competitions.append(competition)

    return render_template('competitionManagement.html', competitions=competitions)


@app.route('/workOnApprovedCompetition/<int:competitionId>', methods=['GET'])
@role_required('cadmin')
def workOnApprovedCompetition(competitionId):
    """
    Fetch all events based on status and render the work page for an approved competition
    """
    session['competition'] = {'competitionId': competitionId}
    source = request.args.get('source', None)

    # query all staff
    with getCursor() as cursor:
        sql = '''SELECT status
                FROM competition
                WHERE competition_id = %s;
        '''
        cursor.execute(sql, (competitionId,))
        competitionStatus = cursor.fetchone()
        sql = '''SELECT 
                    user.user_id,
                    user.username,
                    user.email,
                    user.first_name,
                    user.last_name,
                    staff.role
                FROM 
                    user
                JOIN 
                    staff ON user.user_id = staff.user_id
                WHERE 
                    staff.competition_id = %s
                ORDER BY 
                    LEFT(staff.role, 1);
        '''
        cursor.execute(sql, (competitionId,))
        staffList = cursor.fetchall()
        sql = '''
                SELECT EXISTS (
                    SELECT 1
                    FROM donation_application
                    WHERE status = 'approved' AND competition_id = %s
                ) AS has_donation;
            '''
        cursor.execute(sql, (competitionId,))
        hasDonation = cursor.fetchone().get('has_donation')
        sql = '''
            SELECT *
            FROM message
            WHERE competition_id = %s
            ORDER BY `like` DESC
            LIMIT 1;
        '''
        cursor.execute(sql, (competitionId,))
        hotestMsg = cursor.fetchone()

    planEvents = getEventsByStatus(competitionId, 'plan')
    currentEvents = getEventsByStatus(competitionId, 'current')
    unfinalEvents = getEventsByStatus(competitionId, 'unfinal')
    finalEvents = getEventsByStatus(competitionId, 'final')
    if source:
        return render_template('siteAdminDeleteApprovedCompetition.html',
                               planEvents=planEvents,
                               currentEvents=currentEvents,
                               unfinalEvents=unfinalEvents,
                               finalEvents=finalEvents,
                               staffList=staffList,
                               competitionStatus=competitionStatus,
                               hasDonation=hasDonation,
                               hotestMsg=hotestMsg)
    else:
        msg = session.pop('msg', None)
        return render_template('workOnApprovedCompetition.html',
                               planEvents=planEvents,
                               currentEvents=currentEvents,
                               unfinalEvents=unfinalEvents,
                               finalEvents=finalEvents,
                               staffList=staffList,
                               competitionStatus=competitionStatus,
                               hasDonation=hasDonation,
                               hotestMsg=hotestMsg,
                               msg=msg)


@app.route('/createEvent', methods=["GET", "POST"])
@role_required('cadmin')
def createEvent():
    """
    POST:
    1. Fetch all form data and perform date range validation.
    2. Add the new event to the database and display a success message.
    3. If validation fails, return to the "createEvent" page with the remaining form data and an error message.
    GET:
    1. render createEvent.html with data and msg from session(maybe none)
    """
    if request.method == "POST":
        competitionId = session.get('competition', {})['competitionId']
        title = request.form["title"]
        startDate = request.form["startDate"]
        endDate = request.form["endDate"]
        description = request.form["description"]
        session['event'] = {'title': title, 'description': description}
        if not validateDateRange(startDate, endDate):
            # keep the title and description, so admin needn't input again
            session['msg'] = "The start date can only be after today, and the end date cannot be earlier than the start date."
            return redirect(url_for("createEvent"))

        if 'image' in request.files:
            uploadFilename = uploadImage('image', 'event_images')
            if uploadFilename:
                cursor = getCursor()
                sql = """INSERT INTO event (competition_id,start_date, end_date, title,description,image) 
                        VALUES (%s, %s, %s,%s,%s,%s);"""
                cursor.execute(sql, (competitionId, startDate,
                                     endDate, title, description, uploadFilename))
                eventId = cursor.lastrowid
                session['event']['eventID'] = eventId
                session['event']['image'] = uploadFilename
                session['msg'] = "New Event Created Successfully"
                session['event']['title'] = ''
                session['event']['description'] = ''
                return redirect(url_for('planEventWorkPage', eventId=eventId))
        else:
            session['msg'] = "Please select a file."
            return redirect(url_for('createEvent'))

    elif request.method == "GET":
        event = session.pop('event', {})
        msg = session.pop('msg', None)
        return render_template("createEvent.html", event=event, msg=msg)


@app.route('/planEventWorkPage/<int:eventId>', methods=['GET'])
@role_required('cadmin')
def planEventWorkPage(eventId):
    session['event'] = {'eventId': eventId}
    cursor = getCursor()
    sql = '''SELECT *
            FROM event
            WHERE event_id = %s;
    '''
    cursor.execute(sql, (eventId,))
    eventInfo: dict = cursor.fetchone()

    competitors: list[dict] = getCompetitorsInAnEvent(eventId)
    competitionId = session.get('competition', {})['competitionId']
    sql = '''SELECT DISTINCT c.*
            FROM competitor c
            JOIN candidate ca ON c.competitor_id = ca.competitor_id
            WHERE ca.competition_id = %s
            AND ca.event_id != %s
            AND NOT EXISTS (
                SELECT 1
                FROM candidate ca2
                WHERE ca2.competition_id = ca.competition_id
                AND ca2.competitor_id = ca.competitor_id
                AND ca2.event_id = %s
            );
    '''
    cursor.execute(sql, (competitionId, eventId,  eventId))
    competitorsForSelect: list[dict] = cursor.fetchall()
    msg = session.pop('msg', None)
    return render_template('planEventWorkPage.html',
                           eventInfo=eventInfo,
                           competitors=competitors,
                           competitorsForSelect=competitorsForSelect,
                           msg=msg)


@app.route('/editPlanEventInfo', methods=["POST"])
@role_required('cadmin')
def editPlanEventInfo():
    eventId = session['event'].get('eventId')
    title = request.form["title"]
    startDate = request.form["startDate"]
    endDate = request.form["endDate"]
    description = request.form["description"]
    session['event'] = {'title': title, 'description': description}
    if not validateDateRange(startDate, endDate):
        # keep the title and description, so admin needn't input again
        session['msg'] = "The start date can only be after today, and the end date cannot be earlier than the start date."
        return redirect(url_for("planEventWorkPage", eventId=eventId))
    cursor = getCursor()
    sql = '''UPDATE event
            SET start_date = %s,
                end_date = %s,
                title = %s,
                description = %s
            WHERE event_id = %s;
    '''
    cursor.execute(sql, (startDate, endDate, title,
                   description, eventId))
    session['event']['title'] = ''
    session['event']['description'] = ''
    session['msg'] = "Event Details Updated!"
    return redirect(url_for('planEventWorkPage', eventId=eventId))


@app.route('/updateEventImage', methods=["POST"])
@role_required('cadmin')
def updateEventImage():
    eventId = session['event'].get('eventId')
    if 'image' in request.files:
        uploadFilename = uploadImage('image', 'event_images')
        if uploadFilename:
            cursor = getCursor()
            sql = '''UPDATE event
                    SET image = %s
                    WHERE event_id = %s;
            '''
            cursor.execute(sql, (uploadFilename, eventId))
            session['msg'] = 'Update image successfully'
            return redirect(url_for('planEventWorkPage', eventId=eventId))
        else:
            return redirect(url_for('addCompetitor'))
    else:
        session['msg'] = "Please select a file."
        return redirect(url_for('planEventWorkPage', eventId=eventId))


@app.route('/addCompetitor', methods=["GET", "POST"])
@role_required('cadmin')
def addCompetitor():
    """
    POST:
    1. Fetch all form data and perform file validation.
    2. Add new competitor and new candidate to the database and display a success message.
    3. If validation fails, return to the "addCompetitor" page with the remaining form data and an error message.
    GET:
    1. render addCompetitor.html with data and msg from session(could be none)
    """
    if request.method == "POST":
        eventId = session.get('event', {})['eventId']
        competitionId = session.get('competition', {})['competitionId']
        name = request.form["name"]
        description = request.form["description"]
        session['competitor'] = {'name': name, 'description': description}
        if 'image' in request.files:
            uploadFilename = uploadImage('image', 'competitor_images')
            if uploadFilename:
                cursor = getCursor()
                sql = '''INSERT INTO competitor (name, description, image)
                        VALUES (%s,%s,%s);
                '''
                cursor.execute(sql, (name, description, uploadFilename))
                competitorId = cursor.lastrowid
                sql = '''INSERT INTO candidate (competition_id,competitor_id,event_id)
                        VALUES (%s,%s,%s);
                '''
                cursor.execute(sql, (competitionId, competitorId, eventId))
                session['msg'] = "Competitor Added Successfully!"
                return redirect(url_for('planEventWorkPage', eventId=eventId))
            else:
                return redirect(url_for('addCompetitor'))
        else:
            session['msg'] = "Please select a file"
            return redirect(url_for('addCompetitor'))

    elif request.method == "GET":
        competitor: dict = session.pop('competitor', {})
        msg = session.pop('msg', None)
        return render_template('addCompetitor.html',
                               competitor=competitor,
                               msg=msg)


@app.route('/editCompetitor/', methods=['GET', 'POST'])
@role_required('cadmin')
def editCompetitor():
    eventId = session.get('event')['eventId']

    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        session['competitor'] = {'name': name, 'description': description}
        competitorId = request.form['competitorId']

        if 'image' in request.files and request.files['image'].filename != '':
            uploadFilename = uploadImage('image', 'competitor_images')
            if uploadFilename:
                cursor = getCursor()
                sql = """UPDATE competitor 
                        SET name=%s, description=%s, image=%s
                        WHERE competitor_id=%s; """
                cursor.execute(
                    sql, (name, description, uploadFilename, competitorId))
                session['msg'] = "Edit Successful!"
                return redirect(url_for('planEventWorkPage', eventId=eventId))
            else:
                session['msg'] = 'Please select the correct file.(.png .jpg or .jpeg)'
                return redirect(url_for('editCompetitor', competitorId=competitorId))
        else:
            cursor = getCursor()
            sql = """UPDATE competitor 
                        SET name=%s, description=%s
                        WHERE competitor_id=%s; """
            cursor.execute(
                sql, (name, description, competitorId))
            session.pop('competitor', None)
            return redirect(url_for('planEventWorkPage', eventId=eventId))

    elif request.method == "GET":
        competitorId = request.args.get('competitorId')
        cursor = getCursor()
        sql = """SELECT *
                FROM competitor
                WHERE competitor_id = %s;"""
        cursor.execute(sql, (competitorId,))
        competitor: dict = cursor.fetchone()
        competitorNewInfoButNotUpate = session.pop('competitor', {})
        msg = session.pop('msg', None)
        return render_template('editCompetitor.html',
                               competitor=competitor,
                               competitorNewInfoButNotUpate=competitorNewInfoButNotUpate,
                               competitorId=competitorId,
                               msg=msg)


@app.route('/deleteCandidate/<int:candidateId>', methods=['POST'])
@role_required('cadmin')
def deleteCandidate(candidateId):
    cursor = getCursor()
    sql = """DELETE FROM candidate
            WHERE candidate_id = %s;"""
    cursor.execute(sql, (candidateId,))
    eventId = session.get('event', {})['eventId']
    session['msg'] = "Candidate deleted!"
    return redirect(url_for('planEventWorkPage', eventId=eventId))


@app.route('/selectCandidate/<int:competitorId>')
@role_required('cadmin')
def selectCandidate(competitorId):
    competitionId = session.get('competition', {})['competitionId']
    eventId = session.get('event', {})['eventId']
    cursor = getCursor()
    sql = '''INSERT INTO candidate (competition_id,competitor_id,event_id)
                        VALUES (%s,%s,%s);
                '''
    cursor.execute(sql, (competitionId, competitorId, eventId))
    session['msg'] = "Candidate added!"
    return redirect(url_for('planEventWorkPage', eventId=eventId))


@app.route('/userProfileForAppointment/<int:userId>', methods=['GET'])
@role_required('cadmin')
def userProfileForAppointment(userId):
    competitionId = session.get('competition', {}).get('competitionId')
    canBeCompetitionAdmin = True
    canBeScrutineer = True
    canBeModerator = True

    cursor = getCursor()

    sql_user = '''
        SELECT * 
        FROM user 
        WHERE user_id = %s 
        LIMIT 1;
    '''
    cursor.execute(sql_user, (userId,))
    user = cursor.fetchone()

    sql_staff = '''
        SELECT role 
        FROM staff 
        WHERE competition_id = %s 
        AND user_id = %s;
    '''
    cursor.execute(sql_staff, (competitionId, userId))
    roles = cursor.fetchall()

    if roles:
        for role in roles:
            if role['role'] == 'cadmin':
                canBeScrutineer = False
                canBeCompetitionAdmin = False
            elif role['role'] == 'cscrutineer':
                canBeCompetitionAdmin = False
                canBeScrutineer = False
            elif role['role'] == 'cmoderator':
                canBeModerator = False
    else:
        canBeCompetitionAdmin = True
        canBeScrutineer = True
        canBeModerator = True
    return render_template(
        'userProfileForAppointment.html',
        user=user,
        canBeCompetitionAdmin=canBeCompetitionAdmin,
        canBeScrutineer=canBeScrutineer,
        canBeModerator=canBeModerator
    )


@app.route('/appointCompetitionStaff', methods=['POST'])
@role_required('cadmin')
def appointCompetitionStaff():
    userId = request.form['userId']
    role = request.form['role']
    competitionId = session.get('competition', {})['competitionId']
    cursor = getCursor()
    sql = '''INSERT INTO staff (competition_id, user_id, role)
            VALUES (%s, %s, %s);
    '''
    cursor.execute(sql, (competitionId, userId, role,))
    return redirect(url_for('workOnApprovedCompetition', competitionId=competitionId))


@app.route('/relieveStaff', methods=['POST'])
@role_required('cadmin')
def relieveStaff():
    competitionId = session.get('competition', {})['competitionId']
    userId = request.form['userId']
    role = request.form['role']
    cursor = getCursor()
    sql = '''DELETE FROM staff
            WHERE competition_id = %s
            AND user_id = %s
            AND role = %s;
    
    '''
    cursor.execute(sql, (competitionId, userId, role))
    return redirect(url_for('workOnApprovedCompetition', competitionId=competitionId))


@app.route('/deletePlanEvent', methods=['POST'])
@role_required('cadmin')
def deletePlanEvent():
    competitionId = session.get('competition', {})['competitionId']
    eventId = request.form['eventId']
    cursor = getCursor()
    cursor.execute(
        "UPDATE event SET status = 'ban' WHERE event_id = %s", (eventId,))
    session['msg'] = "Event archived"
    return redirect(url_for('workOnApprovedCompetition', competitionId=competitionId))


@app.route('/applyDeleteCompetition', methods=['GET', 'POST'])
@role_required('cadmin', 'admin')
def applyDeleteCompetition():
    if request.method == 'POST':
        reason = request.form['reason']
        details = request.form['details']
        proposerId = session.get('userData', {})['user_id']
        type = 'delete'
        competitionId = session.get('competition', {})['competitionId']
        if not reason or not details:
            session['msg'] = "Please provide both reason and details for deleting competition"
            return redirect(url_for('applyDeleteCompetition'))
        cursor = getCursor()
        sql = '''INSERT INTO competition_application (proposer_id,theme, description,type,competition_id_delete)
                VALUES (%s,%s, %s,%s,%s);
        '''
        cursor.execute(sql, (proposerId, reason, details, type, competitionId))
        session['msg'] = "Submission successful, awaiting approval"
        return redirect(url_for('dashboard'))
    else:
        msg = session.pop('msg', None)
        return render_template('applyDeleteCompetition.html', msg=msg)


@app.route('/closeMessageBoard', methods=['POST'])
@role_required('cadmin')
def closeMessageBoard():
    competitionId = request.form['competitionId']
    cursor = getCursor()
    sql = '''
        UPDATE competition
        SET status = 'nomsg'
        WHERE competition_id = %s;
    '''
    cursor.execute(sql, (competitionId,))
    return redirect(url_for('workOnApprovedCompetition', competitionId=competitionId))


@app.route('/openMessageBoard', methods=['POST'])
@role_required('cadmin')
def openMessageBoard():
    competitionId = request.form['competitionId']
    cursor = getCursor()
    sql = '''
        UPDATE competition
        SET status = 'open'
        WHERE competition_id = %s;
    '''
    cursor.execute(sql, (competitionId,))
    return redirect(url_for('workOnApprovedCompetition', competitionId=competitionId))


@app.route('/competitionAnnouncement', methods=["GET", "POST"])
@role_required('cadmin')
def competitionAnnouncement():
    competitionId = session.get('competition', {})['competitionId']
    userId = session.get('userData', {})['user_id']
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        cursor = getCursor()
        sql = '''INSERT INTO `announcement` (announcer_id, title, content, competition_id, type)
                VALUES (%s, %s, %s, %s, 'competition');
        '''
        cursor.execute(sql, (userId, title, content, competitionId))
        return redirect(url_for('competitionAnnouncement'))
    else:
        cursor = getCursor()
        sql = '''SELECT * 
                FROM `announcement` 
                WHERE `competition_id` = %s
                ORDER BY `create_at` DESC;
        '''
        cursor.execute(sql, (competitionId,))
        announcements = cursor.fetchall()
        msg = session.pop('msg', None)
        return render_template('competitionAnnouncement.html', announcements=announcements, msg=msg)


@app.route('/deleteCompetitionAnnouncement', methods=['POST'])
@role_required('cadmin')
def deleteCompetitionAnnouncement():
    announcement_id = request.form['announcementId']
    with getCursor() as cursor:
        sql = "DELETE FROM announcement WHERE announcement_id = %s"
        cursor.execute(sql, (announcement_id,))
    session['msg'] = "Announcement Deleted!"
    return redirect(url_for('competitionAnnouncement'))


@app.route('/applyForDonation', methods=["GET", "POST"])
@role_required('cadmin')
def applyForDonation():
    if request.method == 'POST':
        competitionId = session.get('competition', {}).get('competitionId')
        proposerId = session.get('userData', {}).get('user_id')
        charity_name = request.form['charity_name']
        charity_id = request.form['charity_id']
        ird = request.form['ird']
        bank_account = request.form['bank_account']
        description = request.form['description']
        goal = request.form['goal']
        start_date = request.form['start_date']
        with getCursor() as cursor:
            sql = '''INSERT INTO donation_application (competition_id, proposer_id, charity_name, charity_id, ird, bank_account, description, goal, start_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            '''
            cursor.execute(sql, (competitionId, proposerId,
                           charity_name, charity_id, ird,
                           bank_account, description, goal, start_date))
        session['msg'] = "Submission successful, awaiting approval"
        return redirect(url_for('myApplication'))
    else:
        return render_template('applyDonation.html')


@app.route('/donationDetailForCompetitionAdmin')
@role_required('cadmin')
def donationDetailForCompetitionAdmin():
    donationId = session.get('competition', {}).get('competitionId')
    with getCursor() as cursor:
        sql = '''SELECT donation_record.*,user.username 
                FROM donation_record
                LEFT JOIN user ON user.user_id = donation_record.donor_id
                WHERE donation_id = %s
                ORDER BY donation_record.create_at DESC;
        '''
        cursor.execute(sql, (donationId,))
        donationRecords = cursor.fetchall()
        sql = '''
            SELECT DATE(create_at) AS donation_date, 
            SUM(amount) AS total_amount
            FROM donation_record
            WHERE donation_id = %s
            GROUP BY DATE(create_at)
            ORDER BY donation_date;
        '''
        cursor.execute(sql, (donationId,))
        dailyDonation = cursor.fetchall()
        sql = '''
            SELECT DATE_FORMAT(create_at, '%Y-%m') AS donation_month, 
            SUM(amount) AS total_amount
            FROM donation_record
            WHERE donation_id = %s
            GROUP BY donation_month
            ORDER BY donation_month;
        '''
        cursor.execute(sql, (donationId,))
        monthlyDonation = cursor.fetchall()
        sql = '''
            SELECT YEAR(create_at) AS donation_year, 
            SUM(amount) AS total_amount
            FROM donation_record
            WHERE donation_id = %s
            GROUP BY donation_year
            ORDER BY donation_year;
        '''
        cursor.execute(sql, (donationId,))
        yearlyDonation = cursor.fetchall()
    return render_template('donationDetailForCompetitionAdmin.html',
                           donationRecords=donationRecords,
                           dailyDonation=dailyDonation,
                           monthlyDonation=monthlyDonation,
                           yearlyDonation=yearlyDonation)
