from flask import Flask
from flask_login import LoginManager
from .config import Config

login_manager = LoginManager()
login_manager.login_view = "auth.login"

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    login_manager.init_app(app)

    from .auth import auth_bp
    from .upload import upload_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(upload_bp)

    return app
