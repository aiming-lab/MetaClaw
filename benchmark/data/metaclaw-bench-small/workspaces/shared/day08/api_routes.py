"""
API routing configuration for Project Orion
Defines REST API endpoints and their handlers
"""

from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


@app.route('/api/v1/users', methods=['GET'])
def list_users():
    """List all users."""
    return jsonify({"users": []}), 200


@app.route('/api/v1/project/:id', methods=['GET'])
def get_project(id):
    """Get project by ID.

    Note: This route path has a bug - should be /projects/:id (plural)
    """
    return jsonify({"project_id": id, "name": "Sample Project"}), 200


@app.route('/api/v1/metrics', methods=['GET'])
def get_metrics():
    """Get system metrics."""
    return jsonify({"cpu": 45.2, "memory": 68.5}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
