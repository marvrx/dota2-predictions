import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import abort
from .db import get_db
from . import roles


bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None

        if not username:
            error = "Username is required"
        elif not password:
            error = "Password is required"
        elif db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone() is not None:
            error = "Username is not available"

        if error is None:
            db.execute(
                'INSERT INTO user (username, password, role) VALUES (?, ?, ?)', (username, generate_password_hash(password), repr(roles.Roles.USER),)
            )
            db.commit()
            return redirect(url_for('auth.login'))

        flash(error)

    return render_template('auth/register.html')


@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = "Incorrect username."
        elif not check_password_hash(user['password'], password):
            error = "Incorrect password."

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            session['user_points'] = user['points']

            return redirect(url_for('/.index'))

        flash(error)

    return render_template('auth/login.html')


@bp.before_app_request
def load_logged_in_user():
    if 'user_id' not in session:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (session['user_id'],)
        ).fetchone()


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('/.index'))


def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        error = None

        if g.user is None:
            return redirect(url_for('auth.login'))
        else:
            client_user_id = session['user_id']
            db_user = get_db().execute(
                'SELECT id, role FROM user '
                'WHERE id = ?', (client_user_id,)
            ).fetchone()
            if (db_user['role'] != repr(roles.Roles.ADMIN)) and (db_user['id'] != client_user_id):
                abort(403, 'Forbidden')
            return view(**kwargs)

    return wrapped_view


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view
