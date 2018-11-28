import os
from flask import Flask


def create_app():

    app = Flask(__name__, instance_relative_config=True)

    # Set default configurations
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'db'),
    )

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from . import db
    db.init_app(app)

    from . import auth
    app.register_blueprint(auth.bp)

    from . import matches
    app.register_blueprint(matches.bp)
    app.add_url_rule('/', endpoint='index')

    from . import template_utils
    app.jinja_env.filters['formatdatetime'] = template_utils.format_time

    return app
