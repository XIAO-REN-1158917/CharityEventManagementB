import re
from datetime import datetime
from mac import app
from flask import render_template
from flask import redirect
from flask import url_for
from mac.common import getCursor, validateEmpty, role_required, loginRequired
from flask import render_template
from mac.utils import getApplicationsList
from flask import jsonify, request, session


@app.route('/helpCenter', methods=['GET', 'POST'])
@loginRequired
def helpCenter():
    with getCursor() as cursor:
        # Sample FAQs hardcoded, replace with database fetching if necessary
        faqs = [
            {"title": "Delivery", "questions": [{"question": "Why did I receive this email?", "answer": "Details about why you received an email."}, {
                "question": "How does this impact me?", "answer": "Details about how this affects you."}]},
            {"title": "Returns and Refunds", "questions": [{"question": "How do I return my order?", "answer": "Details about returns."}, {
                "question": "When will I receive my refund?", "answer": "Details about refund timing."}]}
        ]

        # Fetch existing user requests
        sql = '''SELECT request.*, user.username
                 FROM request
                 JOIN user ON request.proposer_id = user.user_id
                 ORDER BY request.create_at DESC;'''
        cursor.execute(sql)
        requests = cursor.fetchall()

    return render_template('helpCenter.html', faqs=faqs, requests=requests)


@app.route('/helpCenterWork', methods=['GET', 'POST'])
@role_required('admin', 'helper')
def helpCenterWork():
    helperId = session.get('userData', {}).get('user_id')
    with getCursor() as cursor:
        sql = '''SELECT 
                    COUNT(*) AS total_requests,
                    SUM(CASE WHEN status = 'new' THEN 1 ELSE 0 END) AS new_count,
                    SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) AS open_count,
                    SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) AS resolved_count
                FROM 
                    request;
        '''
        cursor.execute(sql)
        helpCenterOverview = cursor.fetchone()
        if not helpCenterOverview:
            helpCenterOverview = {
                'total_requests': 0,
                'new_count': 0,
                'open_count': 0,
                'resolved_count': 0
            }
        else:
            helpCenterOverview = {key: (value if value is not None else 0)
                                  for key, value in helpCenterOverview.items()}
        sql = '''SELECT 
                    COUNT(*) AS admin_or_helper_count
                FROM 
                    user
                WHERE 
                    role IN ('admin', 'helper');
        '''
        cursor.execute(sql)
        headcount = cursor.fetchone()
        sql = '''SELECT 
                    COUNT(*) AS open_status_count
                FROM 
                    customer_service
                WHERE 
                    status = 'open';
        '''
        cursor.execute(sql)
        busy = cursor.fetchone()
        available = int(headcount['admin_or_helper_count']
                        ) - int(busy['open_status_count'])

        sql = '''SELECT * 
                FROM customer_service
                WHERE helper_id = %s AND status = 'open'
                LIMIT 1;
        '''
        cursor.execute(sql, (helperId,))
        currentWork = cursor.fetchone()
    if request.method == 'GET':
        with getCursor() as cursor:
            sql = '''SELECT 
                        request.*, 
                        user.username
                    FROM 
                        request
                    JOIN 
                        user 
                    ON 
                        request.proposer_id = user.user_id
                    ORDER BY 
                        request.create_at DESC;
            '''
            cursor.execute(sql)
            requests = cursor.fetchall()
    else:
        type = request.form['type']
        if type == 'search':
            search = request.form['search']
            search = re.sub(r"\s+", "", search)
            if not search:
                return redirect(url_for('helpCenterWork'))
            with getCursor() as cursor:
                sql = '''SELECT 
                            request.*, 
                            user.username
                        FROM 
                            request
                        JOIN 
                            user 
                        ON 
                            request.proposer_id = user.user_id
                        WHERE title LIKE %s
                        ORDER BY 
                            request.create_at DESC;
                '''
                search_pattern = f"%{search}%"
                cursor.execute(sql, (search_pattern,))
                requests = cursor.fetchall()
        elif type == 'new':
            with getCursor() as cursor:
                sql = '''SELECT 
                            request.*, 
                            user.username
                        FROM 
                            request
                        JOIN 
                            user 
                        ON 
                            request.proposer_id = user.user_id
                        WHERE request.status = 'new'
                        ORDER BY 
                            request.create_at DESC;
                '''
                cursor.execute(sql)
                requests = cursor.fetchall()
        elif type == 'open':
            with getCursor() as cursor:
                sql = '''SELECT 
                            request.*, 
                            user.username
                        FROM 
                            request
                        JOIN 
                            user 
                        ON 
                            request.proposer_id = user.user_id
                        WHERE request.status = 'open'
                        ORDER BY 
                            request.create_at DESC;
                '''
                cursor.execute(sql)
                requests = cursor.fetchall()
        elif type == 'resolved':
            with getCursor() as cursor:
                sql = '''SELECT 
                            request.*, 
                            user.username
                        FROM 
                            request
                        JOIN 
                            user 
                        ON 
                            request.proposer_id = user.user_id
                        WHERE request.status = 'resolved'
                        ORDER BY 
                            request.create_at DESC;
                '''
                cursor.execute(sql)
                requests = cursor.fetchall()

    return render_template('helpCenterWork.html',
                           helpCenterOverview=helpCenterOverview,
                           headcount=headcount,
                           available=available,
                           requests=requests,
                           currentWork=currentWork)


@app.route('/takeRequest', methods=['POST'])
@role_required('admin', 'helper')
def takeRequest():
    requestId = request.form['requestId']
    helperId = session.get('userData', {}).get('user_id')
    with getCursor() as cursor:
        sql = '''INSERT INTO customer_service (helper_id, request_id, status)
                VALUES (%s, %s, 'open');
        '''
        cursor.execute(sql, (helperId, requestId))
        sql = '''UPDATE request
                SET status = 'open'
                WHERE request_id = %s;
        '''
        cursor.execute(sql, (requestId,))
    return redirect(url_for('helpCenterWork'))


@app.route('/assignRequest', methods=['POST'])
@role_required('admin', 'helper')
def assignRequest():
    requestId = request.form['requestId']
    helperId = request.form['helperId']
    with getCursor() as cursor:
        sql = '''UPDATE request 
                SET status = 'open' 
                WHERE request_id = %s;
        '''
        cursor.execute(sql, (requestId,))

        sql = '''SELECT * 
                FROM customer_service 
                WHERE request_id = %s 
                AND status = 'open';
        '''
        cursor.execute(sql, (requestId,))
        previous = cursor.fetchone()
        if previous:
            sql = '''UPDATE customer_service 
                    SET status = 'drop' 
                    WHERE request_id = %s 
                    AND status = 'open';
            '''
            cursor.execute(sql, (requestId,))

        sql = '''INSERT INTO customer_service (helper_id, request_id, status) 
                VALUES (%s, %s, 'open');
        '''
        cursor.execute(sql, (helperId, requestId))

    print(f"Request ID: {requestId}, Helper ID: {helperId}")
    return redirect(url_for('helpCenterWork'))


@app.route('/requesterDetailForHelper/<int:requesterId>')
@role_required('admin', 'helper')
def requesterDetailForHelper(requesterId):
    with getCursor() as cursor:
        sql = '''
        SELECT *
        FROM user
        WHERE user_id=%s;
        '''
        cursor.execute(sql, (requesterId,))
        user = cursor.fetchone()

        sql = '''SELECT v.vote_id,v.candidate_id,v.ip_address,v.create_at,v.status,
                        ca.competition_id,ca.competitor_id,ca.event_id,ction.theme,e.title,competitor.name
                FROM vote AS v
                LEFT JOIN candidate AS ca ON ca.candidate_id=v.candidate_id
                LEFT JOIN competition ON competition.competition_id=ca.competition_id
                LEFT JOIN competition_application AS ction ON ction.application_id = competition.application_id
                LEFT JOIN `event` AS e ON e.event_id = ca.event_id
                LEFT JOIN competitor ON competitor.competitor_id=ca.competitor_id
                WHERE voter_id=%s
                ORDER BY create_at DESC;
        '''
        cursor.execute(sql, (requesterId,))
        votes = cursor.fetchall()

        sql = '''SELECT dr.record_id,dr.amount,dr.anonymous,dr.create_at,ca.theme,da.charity_name,p.payment_method,p.payment_status
                FROM donation_record AS dr
                LEFT JOIN competition ON dr.donation_id=competition.competition_id
                LEFT JOIN competition_application AS ca ON competition.application_id = ca.application_id
                LEFT JOIN payment AS p ON p.payment_id = dr.record_id
                LEFT JOIN donation_application AS da ON da.competition_id = dr.donation_id
                WHERE dr.donor_id = %s;
        '''
        cursor.execute(sql, (requesterId,))
        donations = cursor.fetchall()

        sql = '''SELECT competition_id 
                    FROM staff
                    WHERE user_id=%s
                    AND `role` = 'cadmin';
        '''
        cursor.execute(sql, (requesterId,))
        competitionDicts = cursor.fetchall()
        competitionIds = [row['competition_id'] for row in competitionDicts]

        if competitionIds:
            placeholders = ','.join(['%s'] * len(competitionIds))
            query = f"""
                    SELECT ction.competition_id, ca.theme, ca.status
                    FROM competition AS ction
                    LEFT JOIN competition_application AS ca ON ction.application_id = ca.application_id
                    WHERE ca.status = 'approved'
                    AND ction.competition_id IN ({placeholders});
                """
            cursor.execute(query, tuple(competitionIds))
            competitions = cursor.fetchall()
        else:
            competitions = None

    return render_template('requesterDetailForHelper.html',
                           user=user,
                           votes=votes,
                           donations=donations,
                           competitions=competitions,
                           requesterId=requesterId)


@app.route('/resolveRequest', methods=['POST'])
@role_required('admin', 'helper')
def resolveRequest():
    requestId = request.form['requestId']
    with getCursor() as cursor:
        sql = '''UPDATE customer_service 
                    SET status = 'resolved' 
                    WHERE request_id = %s 
                    AND status = 'open';
        '''
        cursor.execute(sql, (requestId,))

        sql = '''UPDATE request 
                SET status = 'resolved' 
                WHERE request_id = %s;
        '''
        cursor.execute(sql, (requestId,))
    return redirect(url_for('helpCenterWork'))


@app.route('/dropRequest', methods=['POST'])
@role_required('admin', 'helper')
def dropRequest():
    requestId = request.form['requestId']
    with getCursor() as cursor:
        sql = '''UPDATE request 
                SET status = 'new' 
                WHERE request_id = %s;
        '''
        cursor.execute(sql, (requestId,))

        sql = '''UPDATE customer_service 
                    SET status = 'drop' 
                    WHERE request_id = %s 
                    AND status = 'open';
        '''
        cursor.execute(sql, (requestId,))
    return redirect(url_for('helpCenterWork'))
