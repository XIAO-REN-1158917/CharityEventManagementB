from mac import app
import uuid
import re
import os
from mac.common import getCursor, role_required, validateDateRange, allowedFile, loginRequired
from mac.utils import getEventsByStatus, getCompetitorsInAnEvent, getMyApplicationList, uploadImage
from flask import jsonify, request, session
from flask import render_template
from flask import redirect
from flask import url_for
from werkzeug.utils import secure_filename


@app.route('/pinMessage', methods=['POST'])
@role_required('cadmin', 'cmoderator')
def pinMessage():
    # messageId = request.form['messageId']
    payload = request.get_json()
    messageId = payload['messageId']
    cursor = getCursor()
    sql = '''UPDATE message
            SET type = 'hot'
            WHERE message_id = %s;
    '''
    cursor.execute(sql, (messageId,))
    return {}


@app.route('/unpinMessage', methods=['POST'])
@role_required('cadmin', 'cmoderator')
def unpinMessage():
    # messageId = request.form['messageId']
    payload = request.get_json()
    messageId = payload['messageId']
    cursor = getCursor()
    sql = '''
        UPDATE message
        SET type = 'normal'
        WHERE message_id = %s;
        '''
    cursor.execute(sql, (messageId,))
    return {}


@app.route('/messageManagement')
@role_required('cadmin', 'cmoderator')
def messageManagement():
    competitionIds = session.get('userData', {}).get('cmoderator', [])
    competitionMessage = []
    competitionIdAndTitile = []
    with getCursor() as cursor:
        for competition_id in competitionIds:
            sql = '''SELECT * FROM message WHERE competition_id = %s'''
            cursor.execute(sql, (competition_id,))
            messages = cursor.fetchall()
            competitionMessage.extend(messages)

            sql = '''SELECT c.competition_id,ca.theme
                    FROM competition AS c
                    LEFT JOIN competition_application AS ca ON ca.application_id=c.application_id
                    WHERE c.competition_id=%s;
            '''
            cursor.execute(sql, (competition_id,))
            idAndTitle = cursor.fetchone()
            competitionIdAndTitile.append(idAndTitle)

        sql = '''SELECT * 
                    FROM reply 
            '''
        cursor.execute(sql)
        replies = cursor.fetchall()

    return render_template('messageManagement.html',
                           messages=competitionMessage,
                           replies=replies,
                           competitionIdAndTitile=competitionIdAndTitile)


@app.route('/deleteMessage', methods=['POST'])
@loginRequired
def deleteMessage():
    # messageId = request.form['messageId']
    # next_page = request.form['next']

    payload = request.get_json()
    messageId = payload['messageId']
    next_page = payload['next']
    cursor = getCursor()
    sql = ''' DELETE FROM message 
            WHERE message_id = %s;'''
    cursor.execute(sql, (messageId,))
    return {}


@app.route('/deleteReply', methods=['POST'])
@loginRequired
def deleteReply():
    # replyId = request.form['replyId']
    # next_page = request.form['next']

    payload = request.get_json()
    replyId = payload['replyId']
    next_page = payload['next']

    cursor = getCursor()
    sql = ''' DELETE FROM reply 
            WHERE reply_id = %s;'''
    cursor.execute(sql, (replyId,))
    return {'success': True}


@app.route('/deleteMessageModerator', methods=['POST'])
@loginRequired
def deleteMessageModerator():
    messageId = request.form['messageId']
    next_page = request.form['next']
    cursor = getCursor()
    sql = ''' DELETE FROM message 
            WHERE message_id = %s;'''
    cursor.execute(sql, (messageId,))
    return redirect(url_for(next_page))


@app.route('/deleteReplyModerator', methods=['POST'])
@loginRequired
def deleteReplyModerator():
    replyId = request.form['replyId']
    next_page = request.form['next']
    cursor = getCursor()
    sql = ''' DELETE FROM reply 
            WHERE reply_id = %s;'''
    cursor.execute(sql, (replyId,))
    return redirect(url_for(next_page))


@app.route('/publicProfile', methods=['GET', 'POST'])
@loginRequired
def publicProfile():
    """
    1. receive user_id (via sender_id)
    2. Fetch user_details considered as public details only
    3. pass to template for display
    Return:
    publicProfile.html
    """
    userId = request.args.get('userId')
    cursor = getCursor()
    sql = ''' SELECT user.user_id, user.username, user.description, user.location, user.profile_image, user.role, user.message_board
        FROM user
        WHERE user_id = %s;
        '''
    cursor.execute(sql, (userId,))
    userPublicDetails = cursor.fetchall()

    sql = '''
        SELECT competition_application.theme, message.message_id, message.title, message.content, message.create_at, message.like
        FROM message
        RIGHT JOIN competition ON message.competition_id = competition.competition_id
        RIGHT JOIN competition_application ON competition.application_id = competition_application.application_id
        WHERE message.sender_id = %s;   
        '''
    cursor.execute(sql, (userId,))
    userMessages = cursor.fetchall()

    sql = '''
        SELECT competition_application.theme, message.message_id, message.title, reply.reply_id, reply.content, reply.create_at
        FROM reply
        RIGHT JOIN message ON reply.message_id = message.message_id
        RIGHT JOIN competition ON message.competition_id = competition.competition_id
        RIGHT JOIN competition_application ON competition.application_id = competition_application.application_id
        WHERE reply.sender_id = %s;   
        '''
    cursor.execute(sql, (userId,))
    userReplies = cursor.fetchall()

    sql = '''
        SELECT DISTINCT event.event_id, event.title, event.image
        FROM event
        RIGHT JOIN candidate ON event.event_id = candidate.event_id
        RIGHT JOIN vote ON candidate.candidate_id = vote.candidate_id
        WHERE vote.voter_id = %s;
        '''
    cursor.execute(sql, (userId,))
    eventsVotedIn = cursor.fetchall()

    return render_template('publicProfile.html',
                           userPublicDetails=userPublicDetails,
                           userMessages=userMessages,
                           userReplies=userReplies,
                           eventsVotedIn=eventsVotedIn)


@app.route('/publicProfileListing', methods=['GET', 'POST'])
@loginRequired
def publicProfileListing():
    """
    Handle user search and display public user listing page.

    GET:
    It queries and displays a list of all users, ordered by username where user has indicated they want their accounts visible on the public listing.

    POST:
    1. It processes the search query provided by the user,
    2. trims whitespace from the search input,
    3. performs a case-insensitive and partial match search for users whose username matches the search query,
    4. displays the search results.

    Render the template, show the results.
    Returns:
    userManagement.html with results shown OR
    userManagement.html with error message (if no matching results)
    """

    cursor = getCursor()
    # If GET, show all users.
    if request.method == "GET":
        cursor.execute(
            "SELECT user.user_id, user.username, user.description, user.location, user.profile_image, user.role FROM user WHERE public = 'visible' ORDER BY username;"
        )
        userList = cursor.fetchall()
        return render_template("publicProfileListing.html", userList=userList)
    # If POST, show users based on the search results.
    if request.method == "POST":
        name = request.form["name"]
        # Trim space
        name = re.sub(r"\s+", "", name)
        if not name:
            return redirect(url_for("publicProfileListing"))

        sql = """SELECT user.user_id, user.username, user.description, user.location, user.profile_image, user.role 
        FROM user
        WHERE CONCAT(username) LIKE %s AND public = 'visible'
        ORDER BY username;"""
        # Partial match
        cursor.execute(sql, ("%" + name + "%",))
        userList = cursor.fetchall()
        # If no data matched, send a error message.
        if not userList:
            msg = "No matching results."
            return render_template(
                "publicProfileListing.html", userList=userList, msg=msg
            )
        return render_template("publicProfileListing.html", userList=userList)


@app.route('/userMessageBoardBan', methods=['POST'])
@role_required('cadmin', 'cmoderator')
def userMessageBoardBan():
    """
    1. Receive userId and messageBoard status
    2. update user in user table to status sent in messageBoard
    3. if 'banned' = can no longer interact with message board
    Return:
    publicProfile.html
    """
    messageBoard = request.form["messageBoard"]
    userId = request.form["userId"]
    cursor = getCursor()
    sql = '''
        UPDATE user
        SET message_board=%s
        WHERE user_id=%s;
    '''
    cursor.execute(sql, ((messageBoard, userId)))
    return redirect(url_for("profile", userId=userId))
