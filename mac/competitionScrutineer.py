from mac import app
import uuid
import os
from mac.common import getCursor, validateDateRange, allowedFile, role_required
from mac.utils import getEventsByStatus, getCompetitorsInAnEvent, getMyApplicationList, uploadImage
from flask import jsonify, request, session
from flask import render_template
from flask import redirect
from flask import url_for
from werkzeug.utils import secure_filename


@app.route('/staffCompetitionList')
@role_required('cscrutineer', 'cadmin')
def staffCompetitionList():
    """
    1. GET request from dashboard
    2. Fetch all competitions user has a role of cadmin or cscrutineer in
    3. Display in a list form via template
    4. User can then click to see vote details for that competition
    Returns:
    staffCompetitionList.html
    """
    userId = session.get('userData', {})['user_id']
    cursor = getCursor()
    sql = """
        SELECT competition.competition_id, competition_application.theme, staff.role
        FROM competition
        RIGHT JOIN staff
        ON competition.competition_id = staff.competition_id
        RIGHT JOIN competition_application
        ON competition.application_id = competition_application.application_id
        WHERE staff.user_id = %s;
        """
    cursor.execute(sql, (userId,))
    userCompetitionRoleList = cursor.fetchall()
    return render_template('staffCompetitionList.html', userCompetitionRoleList=userCompetitionRoleList)


@app.route('/voteDetailsEvent/<int:competitionId>', methods=['GET'])
@role_required('cscrutineer', 'cadmin')
def voteDetailsEvent(competitionId):
    """
    1. Receive competition_id from staffCompetitionList
    2. Fetch event_id for 'current' event for that competition
    3. Fetch total votes for each day of 'current' event
    4. Pass to template for display 
    Returns:
    voteDetailsEvent.html
    """
    session['competition'] = {'competitionId': competitionId}
    cursor = getCursor()
    sql = "SELECT * FROM event WHERE event.competition_id=%s AND event.status='current';"
    cursor.execute(sql, (competitionId,))
    eventDetails = cursor.fetchall()
    eventId = eventDetails[0]['event_id']
    sql = """
        SELECT create_date, COUNT(*) AS all_votes
        FROM (
        SELECT DATE_FORMAT(vote.create_at, '%Y-%m-%d') AS create_date
        FROM vote
        LEFT JOIN candidate
        ON vote.candidate_id = candidate.candidate_id
        LEFT JOIN event
        ON candidate.event_id = event.event_id
        WHERE candidate.event_id = %s
	        AND vote.create_at BETWEEN event.start_date AND (CURRENT_DATE() - INTERVAL 1 DAY)
            AND vote.status = 'valid'
        GROUP BY vote.create_at
        ) AS subquery
        GROUP BY create_date;
        """
    cursor.execute(sql, (eventId,))
    votesPerDay = cursor.fetchall()
    return render_template('voteDetailsEvent.html', eventDetails=eventDetails, votesPerDay=votesPerDay)


@app.route('/scrutineerEventList/<int:competitionId>', methods=['GET'])
@role_required('cscrutineer', 'cadmin')
def scrutineerEventList(competitionId):
    """
    1. Receive competition_id from staffCompetitionList
    2. Fetch event_id for 'current' and 'unfinal' events for that competition
    3. Fetch event details for 'current' and 'unfinal' events for that competition
    4. Pass to template for display 
    5. User can click review votes to see all votes for that event
    Returns:
    scrutineerEventList.html
    """
    session['competition'] = {'competitionId': competitionId}
    cursor = getCursor()
    sql = "SELECT * FROM event WHERE event.competition_id=%s AND event.status='current';"
    cursor.execute(sql, (competitionId,))
    currentEvent = cursor.fetchall()
    sql = "SELECT * FROM event WHERE event.competition_id=%s AND event.status='unfinal';"
    cursor.execute(sql, (competitionId,))
    unfinalEvents = cursor.fetchall()

    return render_template('scrutineerEventList.html', currentEvent=currentEvent, unfinalEvents=unfinalEvents)


@app.route('/reviewVotes/<int:eventId>', methods=['GET'])
@role_required('cscrutineer', 'cadmin')
def reviewVotes(eventId):
    """
    1. Receive event_id from scrutineerEventList
    2. Fetch all votes for that event_id
    3. Fetch all event details for that event
    3. Pass to template for display 
    Returns:
    reviewVotes.html
    """
    session['event'] = {'eventId': eventId}
    cursor = getCursor()
    sql = """
        SELECT user.user_id, user.username, user.email, user.first_name, user.last_name, vote.vote_id, vote.ip_address, vote.create_at, 
        competitor.name AS competitor_name, competitor.image AS competitor_image
        FROM user
        LEFT JOIN vote ON user.user_id = vote.voter_id
        LEFT JOIN candidate ON vote.candidate_id = candidate.candidate_id
        LEFT JOIN competitor ON candidate.competitor_id = competitor.competitor_id
        WHERE candidate.event_id = %s AND vote.status = 'valid';
        """
    cursor.execute(sql, (eventId,))
    votesToReview = cursor.fetchall()
    sql = "SELECT * FROM event WHERE event_id = %s"
    cursor.execute(sql, (eventId,))
    eventDetails = cursor.fetchone()
    msg = session.pop('msg', None)
    return render_template('reviewVotes.html', votesToReview=votesToReview, eventDetails=eventDetails, msg=msg)


@app.route('/approveEvent', methods=['POST'])
@role_required('cscrutineer', 'cadmin')
def approveEvent():
    """
    Handles the approval process for an event
    1. Receive eventId
    2. Determines the competitor with the most votes for the specific event
    3. Calculates the winners percentage of total votes
    4. Inserts the result into the database and updates the event status to 'approved'
    5. Pass to template for rendering
    Returns:
    scrutineerEventList.html
    """
    eventId = request.form['eventId']
    if not eventId:
        return render_template('404.html')

    cursor = getCursor()
    sql = """
        SELECT competition.competition_id 
        FROM competition
        LEFT JOIN event
        ON competition.competition_id = event.competition_id
        WHERE event.event_id = %s;    
        """
    cursor.execute(sql, (eventId,))
    dictCompetitionId = cursor.fetchone()
    getCompetitionId = dictCompetitionId['competition_id']
    competitionId = int(getCompetitionId)

    sql = """
        SELECT COUNT(v.candidate_id) AS vote, cand.candidate_id
            FROM vote AS v
            LEFT JOIN candidate AS cand ON v.candidate_id = cand.candidate_id
            WHERE cand.event_id = %s
            GROUP BY cand.candidate_id
            ORDER BY COUNT(v.candidate_id) DESC
            LIMIT 1;
        """
    cursor.execute(sql, (eventId,))
    votesAndCandidateId = cursor.fetchone()

    if not votesAndCandidateId:
        msg = "No votes found for this event"
        return redirect(url_for('reviewVotes', msg=msg, eventId=eventId))

    vote = votesAndCandidateId['vote']
    candidateId = votesAndCandidateId['candidate_id']

    sql = '''SELECT COUNT(v.candidate_id) AS total_votes
            FROM vote AS v
            LEFT JOIN candidate AS cand ON v.candidate_id = cand.candidate_id
            WHERE cand.event_id = %s;'''
    cursor.execute(sql, (candidateId,))
    totalVotesResult = cursor.fetchone()

    if not totalVotesResult:
        msg = "No votes found for this event"
        return redirect(url_for('reviewVotes', msg=msg, eventId=eventId))

    totalVotes = totalVotesResult['total_votes']
    winnerPercentage = int(vote) / int(totalVotes)*100 if totalVotes else 0

    sql = """ 
        INSERT INTO result (candidate_id, total_votes, percentage)
            VALUES (%s, %s, %s);
         """
    cursor.execute(sql, (candidateId, totalVotes, winnerPercentage))

    sql = " UPDATE event SET status = 'final' WHERE event_id = %s "
    cursor.execute(sql, (eventId,))
    msg = 'Approved!'
    return redirect(url_for('scrutineerEventList', msg=msg, competitionId=competitionId))


@app.route('/ipAddressVotes', methods=['GET'])
@role_required('cscrutineer', 'cadmin')
def ipAddressVotes():
    """
    1. Receive event_id and ip_address
    2. Fetch all votes from that ip_address for that event_id
    3. Pass to template for rendering
    Returns:
    ipAddressPage
    """
    ipAddress = request.args.get('ipAddress')
    eventId = request.args.get('eventId')
    cursor = getCursor()
    sql = """
        SELECT user.user_id, user.username, user.email, user.first_name, user.last_name, vote.vote_id, vote.ip_address, vote.create_at, 
        competitor.name AS competitor_name, competitor.image AS competitor_image
        FROM user
        LEFT JOIN vote ON user.user_id = vote.voter_id
        LEFT JOIN candidate ON vote.candidate_id = candidate.candidate_id
        LEFT JOIN competitor ON candidate.competitor_id = competitor.competitor_id
        WHERE vote.ip_address = %s AND candidate.event_id = %s AND vote.status = 'valid';
        """
    cursor.execute(sql, (ipAddress, eventId))
    votesForIP = cursor.fetchall()
    sql = "SELECT * FROM event WHERE event_id = %s"
    cursor.execute(sql, (eventId,))
    eventDetails = cursor.fetchone()
    msg = session.pop('msg', None)
    return render_template('ipAddressPage.html', 
                           votesForIP=votesForIP, 
                           eventDetails=eventDetails,
                           msg=msg)


@app.route('/voteCheck', methods=['POST'])
@role_required('cscrutineer', 'cadmin')
def voteCheck():
    """
    1. Receive event_id from reviewVotes
    2. Fetch all ip_address with more than 3 votes assigned to them for the event.
    Ordered from highest number of votes to lowest number of votes
    3. Pass to template for rendering
    Returns:
    multipleVoteIPs
    """
    eventId = request.form['eventId']
    cursor = getCursor()
    sql = """
        SELECT subquery.ip_address, COUNT(subquery.vote_id) AS nu_of_votes
        FROM (
        SELECT vote.vote_id, vote.ip_address
        FROM vote
        LEFT JOIN candidate
        ON vote.candidate_id = candidate.candidate_id
        WHERE candidate.event_id = %s AND vote.status = 'valid'
        ) AS subquery
        GROUP BY subquery.ip_address
        HAVING COUNT(subquery.vote_id) >= 3
        ORDER BY nu_of_votes DESC;
        """
    cursor.execute(sql, (eventId,))
    multipleVotes = cursor.fetchall()
    sql = "SELECT * FROM event WHERE event_id = %s"
    cursor.execute(sql, (eventId,))
    eventDetails = cursor.fetchone()
    return render_template('multipleVoteIPs.html', multipleVotes=multipleVotes, eventDetails=eventDetails)


@app.route('/invalidateVote', methods=['GET', 'POST'])
@role_required('cscrutineer', 'cadmin')
def invalidateVote():
    """
    1. Receive vote_id's for all checked votes
    2. Receive event_id
    3. Mark all votes in vote table with those vote_id's as 'invalid'
    4. Pass event_id for redirect to reviewVotes
    Return:
    reviewVotes.html
    """
    voteIds = request.form.getlist('invalidvote[]')
    userIds = request.form.getlist('invaliduser[]')
    eventId = request.form['eventId']
    ipAddress = request.form['ipAddress']


    if not voteIds:
        session['msg'] = "You have not selected any votes to invalidate. You must invalidate an accounts vote if you wish to inactivate a user account."
        return redirect(url_for('ipAddressVotes', ipAddress=ipAddress, eventId=eventId))
    else:
        cursor = getCursor()
        for id in voteIds:
            sql = """
                UPDATE vote
                SET status = 'invalid'
                WHERE vote_id = %s;
                """
            cursor.execute(sql, (id,))

        if not userIds:
            session['msg'] = "Votes have been marked as invalid!"
            return redirect(url_for('reviewVotes', eventId=eventId))
        else:
            cursor = getCursor()
            for id in userIds:
                sql = """
                    UPDATE user
                    SET status = 'inactive'
                    WHERE user_id = %s;
                    """
                cursor.execute(sql, (id,))
            session['msg'] = "Votes have been marked as invalid. Accounts have been inactivated!"
            return redirect(url_for('reviewVotes', eventId=eventId))