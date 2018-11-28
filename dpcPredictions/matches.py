from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from .auth import login_required, admin_required
from .db import get_db
from .utils import is_integer
from _datetime import datetime, timedelta

bp = Blueprint('/', __name__)

CORRECT_PREDICTION_INCREMENT = 50


@bp.route('/', methods=('GET', 'POST',))
def index():
    if request.method == 'POST':
        handle_prediction_submission()

    matches = get_current_matches()

    content = []

    for match in matches:
        entry = dict()
        entry['match'] = match

        team_a = match['team_a']
        team_b = match['team_b']
        entry['team_a_logo'] = get_logo_path(team_a)
        entry['team_b_logo'] = get_logo_path(team_b)

        content.append(entry)

    return render_template('matches/index.html', matches=content, leaderboard=setup_leaderboard())


def setup_leaderboard():
    db = get_db()
    return db.execute(
        'SELECT username, points FROM user '
        'ORDER BY points ASC '
        'LIMIT 10'
    ).fetchall()


def get_current_matches():
    return get_db().execute(
        'SELECT * FROM match ORDER BY match_date ASC'
    ).fetchall()


def handle_prediction_submission():
    db = get_db()
    error = None

    f = request.form
    for key in f.keys():
        for value in f.getlist(key):
            predictions = db.execute(
                'SELECT * FROM predictions '
                'WHERE user_id = ? AND match_id = ?',
                (g.user['id'], key)
            ).fetchall()

            if predictions:
                error = "Predictions already submitted."
            elif not is_submission_date_valid(key):
                error = "Submission period for one or more selected matches has passed."
            else:
                db.execute(
                    'INSERT INTO predictions (user_id, match_id, prediction) '
                    'VALUES (?, ?, ?)',
                    (g.user['id'], key, value,)
                )
                db.commit()

    flash(error)


def is_submission_date_valid(match_id):
    now = datetime.now()

    cursor = get_db().execute(
        'SELECT match_date FROM match WHERE id = ?',
        match_id
    ).fetchone()

    match_date_string = cursor['match_date']
    match_date = datetime.strptime(match_date_string, '%Y-%m-%dT%H:%M')

    return now < match_date


@bp.route('/standings')
def standings():
    db = get_db()
    teams = db.execute(
        'SELECT * FROM team ORDER BY points DESC '
    ).fetchall()

    organizations = []

    for team in teams:
        org = dict()
        org['team'] = team

        team_name = team['name']
        roster = db.execute(
            'SELECT nickname FROM player WHERE team = ?', (team_name,)
        )
        org['roster'] = roster
        organizations.append(org)

    return render_template('matches/standings.html', orgs=organizations, leaderboard=setup_leaderboard())


@bp.route('/addMatch', methods=('GET', 'POST'))
@login_required
@admin_required
def add_match():
    if request.method == 'POST':
        # Form data
        team_a = request.form['team_a']
        team_b = request.form['team_b']
        tournament = request.form['tournament']
        rounds = request.form['rounds']
        match_date = request.form['match_date']
        timezone_offset = request.form['timezone-offset']

        error = None

        if get_team_from_db(team_a) is None:
            error = '{} does not exist.'.format(team_a)
        elif get_team_from_db(team_b) is None:
            error = '{} does not exits'.format(team_b)
        elif rounds is None or not is_integer(rounds):
            error = 'Rounds must be an integer.'

        if error is not None:
            flash(error)
        else:

            date = datetime.strptime(match_date, '%Y-%m-%dT%H:%M')
            utc_date = (date + timedelta(minutes=float(timezone_offset)))

            db = get_db()
            db.execute(
                'INSERT INTO match (team_a, team_b, team_a_score, team_b_score, tournament, rounds, match_date, winner)'
                ' VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (team_a, team_b, 0, 0, tournament, rounds, utc_date, '')
            )

            db.commit()
            return redirect(url_for('/.index'))

    return render_template('matches/addMatch.html')


@bp.route('/addTeam', methods=('GET', 'POST'))
@login_required
@admin_required
def add_team():
    if request.method == 'POST':
        name = request.form['name']
        points = request.form['points']
        region = request.form['region']
        earnings = request.form['earnings']
        error = None

        if not name:
            error = "Name is a required field."
        elif not region:
            error = "Region is a required field."

        if error is not None:
            flash(error)
        else:
            if not points:
                points = 0
            else:
                points = int(points)

            if not earnings:
                earnings = 0
            else:
                earnings = int(earnings)

            logo_path = build_logo_path(name)

            db = get_db()
            db.execute(
                'INSERT INTO team (name, points, region, earnings, logo_path) '
                'VALUES (?, ?, ?, ?, ?)',
                (name, points, region, earnings, logo_path)
            )
            db.commit()
            return redirect(url_for('matches.standings'))

    return render_template('matches/addTeam.html')


def build_logo_path(name):
    prefix = 'img/logos/logo_'
    suffix = '.png'
    filename = name.lower().replace(' ', '_')
    return prefix + filename + suffix


@bp.route('/<string:team_name>/updateTeam', methods=('GET', 'POST',))
@login_required
@admin_required
def update_team(team_name):
    team = get_team(team_name)

    if request.method == 'POST':
        name = request.form['name']
        points = request.form['points']
        region = request.form['region']
        earnings = request.form['earnings']
        error = None

        if not name:
            error = "Name is a required field."
        elif not region:
            error = "Region is a required field."
        elif not points:
            error = "Points is a required field."
        elif not earnings:
            error = "Earnings is a required field."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE team SET name = ?, points = ?, region = ?, earnings = ?'
                'WHERE name = ?',
                (name, points, region, earnings, name)
            )
            db.commit()
            return redirect(url_for('/.standings'))

    return render_template('matches/updateTeam.html', team=team)


@bp.route('/<string:team_name>/removeTeam', methods=('POST',))
@login_required
@admin_required
def remove_team(team_name):
    # Will abort request if no such team exists in the db
    get_team(team_name)
    db = get_db()
    db.execute('DELETE FROM team WHERE name = ?', (team_name,))
    db.commit()
    return redirect(url_for('matches.standings'))


def get_team(team_name):
    team = get_team_from_db(team_name)

    if team is None:
        abort(404, 'Team could not be found.')

    return team


def get_team_from_db(team_name):
    return get_db().execute(
        'SELECT * FROM team WHERE name = ?',
        (team_name,)
    ).fetchone()


def get_logo_path(team_name):
    return get_db().execute(
        'SELECT logo_path from team WHERE name = ?', (team_name,)
    ).fetchone()['logo_path']


@bp.route('/<int:match_id>/updateMatch', methods=('GET', 'POST',))
@login_required
@admin_required
def update_match(match_id):
    match = get_match(match_id)

    if request.method == 'POST':
        team_a_score = request.form['team_a_score']
        team_b_score = request.form['team_b_score']
        winner = request.form['winner']
        error = None

        if not team_a_score:
            error = "Team_A_Score is a required field."
        elif not team_b_score:
            error = "Team_B_Score is a required field."
        elif not winner:
            error = "Winner is a required field."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE match SET team_a_score = ?, team_b_score = ?, winner = ?'
                'WHERE id = ?',
                (team_a_score, team_b_score, winner, match_id)
            )
            db.commit()
            update_leaderboards(match_id)
            return redirect(url_for('/.index'))

    return render_template('matches/updateMatch.html', match=match)


def get_match(match_id):
    match = get_db().execute(
        'SELECT * FROM match WHERE id = ?',
    str(match_id)
    ).fetchone()

    if match is None:
        abort(404, 'Match could not be found.')

    return match


def update_leaderboards(match_id, winner):
    db = get_db()
    correct_predictions = db.execute(
        'SELECT user_id FROM predictions WHERE match_id = ? AND prediction = ?',
        (match_id, winner)
    ).fetchall()

    for prediction in correct_predictions:
        user_id = prediction['user_id']
        new_points = get_points_for_user(user_id) + CORRECT_PREDICTION_INCREMENT

        db.execute(
            'UPDATE user SET points = ? '
            'WHERE id = ?',
            (new_points, user_id)
        )
        db.commit()


def get_points_for_user(user_id):
    return get_db().execute(
        'SELECT points from user WHERE id = ?',
        user_id
    ).fetchone()['points']
