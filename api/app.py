from flask import Flask
from config import Config
from routes.health import health_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register blueprints
    app.register_blueprint(health_bp)
    # Stage 2 — uncomment as you build them:
    # from routes.documents import documents_bp
    # app.register_blueprint(documents_bp)
    # from routes.query import query_bp
    # app.register_blueprint(query_bp)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)