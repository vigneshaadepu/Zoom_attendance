"""
EduTrack — Flask Application Factory
"""
import os
import logging
from flask import Flask
from app.config import config_map
from app.extensions import db, login_manager, mail, migrate


def create_app(config_name: str = "development") -> Flask:
    app = Flask(__name__, instance_relative_config=False)

    # Load configuration
    cfg = config_map.get(config_name, config_map["default"])
    app.config.from_object(cfg)

    # Ensure report output dir exists
    os.makedirs(os.path.join(app.root_path, "static", "reports"), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "ml", "train_data"), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    # User loader for Flask-Login
    from app.models import Professor

    @login_manager.user_loader
    def load_user(user_id):
        return Professor.query.get(int(user_id))

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.students import students_bp
    from app.routes.sessions import sessions_bp
    from app.routes.reports import reports_bp
    from app.routes.webhook import webhook_bp
    from app.routes.api import api_bp
    from app.routes.courses import courses_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(sessions_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(webhook_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(courses_bp)

    # Template context processors
    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        return dict(current_user=current_user)

    # Enforce active course selection for management routes
    @app.before_request
    def enforce_course_selection():
        from flask import request, redirect, url_for, session, flash
        from flask_login import current_user
        
        if not current_user.is_authenticated:
            return
            
        ignored_blueprints = ["auth", "courses", "webhook", "static"]
        if request.blueprint and request.blueprint not in ignored_blueprints:
            if not session.get("active_course_id"):
                flash("Please select a course to continue.", "info")
                return redirect(url_for("courses.list_courses"))

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Create tables if they don't exist (dev convenience)
    with app.app_context():
        db.create_all()

    return app
