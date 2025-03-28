from typing import Literal, Optional
from mac.common import getCursor
from typing import Literal
from flask import jsonify, request, session
from flask import redirect
from flask import url_for
from werkzeug.utils import secure_filename
import uuid
import os
from mac.common import getCursor, validateDateRange, allowedFile
from mac import app


def getUserRole(userId) -> set:
    roleSet = set()
    cursor = getCursor()
    sql = '''SELECT role
            FROM user
            WHERE user_id = %s;
    '''
    cursor.execute(sql, (userId,))
    userRole: dict = cursor.fetchone()
    role = userRole['role']
    if role == 'admin':
        roleSet.update(['voter', 'admin'])
    elif role == 'helper':
        roleSet.update(['voter', 'helper'])
    else:
        roleSet.add('voter')

    sql = '''SELECT DISTINCT role
            FROM staff
            WHERE user_id = %s;
    '''
    cursor.execute(sql, (userId,))
    roles: list[dict] = cursor.fetchall()
    if roles:
        for role in roles:
            roleSet.add(role['role'])
    return roleSet


def getCompetitionForStaff(userId: int, role: str) -> list:
    competitionIdList = []
    cursor = getCursor()
    sql = '''SELECT competition_id 
            FROM staff 
            WHERE user_id = %s AND role = %s;
    '''
    cursor.execute(sql, (userId, role))
    competitionIdDict = cursor.fetchall()
    competitionIdList = [competitionId['competition_id']
                         for competitionId in competitionIdDict]
    return competitionIdList


def getRunningCompetitions() -> list[dict]:
    """
    all competition has been approved and has at least one current event.
    """
    cursor = getCursor()
    sql = '''SELECT ca.theme
            FROM competition_application ca
            JOIN competition c ON ca.application_id = c.application_id
            JOIN event e ON c.competition_id = e.competition_id
            WHERE ca.status = 'approved'
            AND e.status = 'current';
    '''
    cursor.execute(sql)
    runningCompetitions = cursor.fetchall()
    return runningCompetitions


def getEventsByStatus(competitionId: Optional[int],
                      status: Literal['plan', 'current', 'unfinal', 'final', 'ban']) -> list[dict]:
    """
    This API can fetch events of a specific competition based on the event's status.
    If competitionId is None, it will fetch events based only on status.

    @param: competitionId (Optional[int])
    @param: status (Literal('plan', 'current', 'unfinal', 'final', 'ban'))
    @return: events (list[dict])
    """
    cursor = getCursor()
    sql = '''
        SELECT * 
        FROM event
        WHERE status = %s
        AND (%s IS NULL OR competition_id = %s)
        ORDER BY start_date ASC;
    '''
    cursor.execute(sql, (status, competitionId, competitionId))
    events = cursor.fetchall()
    return events


def getCompetitorsInAnEvent(eventId: int) -> list[dict]:
    cursor = getCursor()
    sql = '''SELECT DISTINCT c.*, ca.candidate_id
            FROM competitor c
            JOIN candidate ca ON c.competitor_id = ca.competitor_id
            WHERE ca.event_id = %s
            ORDER BY c.competitor_id;
    '''
    cursor.execute(sql, (eventId,))
    competitors = cursor.fetchall()
    return competitors


def getApplicationsList(type: Literal['competition_application', 'donation_application', 'request'],
                        status: Literal['pending', 'approved', 'declined', 'new', 'open', 'resolved'],
                        approverId: int) -> list[dict]:
    cursor = getCursor()
    sql = f'''SELECT a.*, user.username AS proposer_name
            FROM {type} AS a
            JOIN user ON a.proposer_id = user.user_id
            WHERE a.status = %s
            AND a.proposer_id != %s
            ORDER BY a.create_at ASC;
    '''  # Because the table name is controlled by the backend code, it is safe.
    cursor.execute(sql, (status, approverId))
    applications = cursor.fetchall()
    return applications


def getMyApplicationList(type: Literal['competition_application', 'donation_application', 'request'],
                         status: Optional[Literal['pending', 'approved', 'declined', 'new', 'open', 'resolved']],
                         proposerId: int) -> list[dict]:
    cursor = getCursor()

    if status == 'approved' and type == 'competition_application':
        sql = f'''
        SELECT a.*, c.competition_id
        FROM {type} AS a
        LEFT JOIN competition AS c
        ON a.application_id = c.application_id
        WHERE (%s IS NULL OR a.status = %s)
        AND a.proposer_id = %s
        AND c.status = 'open'
        ORDER BY a.create_at ASC;
    '''
    else:
        sql = f'''
            SELECT a.*
            FROM {type} AS a
            WHERE (%s IS NULL OR a.status = %s)
            AND a.proposer_id = %s
            ORDER BY a.create_at ASC;
        '''

    cursor.execute(sql, (status, status, proposerId))
    myApplications = cursor.fetchall()
    return myApplications


def uploadImage(elementName: str, category: str):
    file = request.files[elementName]
    if file and allowedFile(file.filename):
        filename = secure_filename(file.filename)
        filename = str(uuid.uuid4()) + "_" + filename
        file.save(os.path.join(
            app.config['UPLOAD_FOLDER'], category, filename))
        return filename
    else:
        return False
    