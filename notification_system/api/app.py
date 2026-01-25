import os
import logging
from typing import Any
from flask import Flask, request, jsonify
from celery import Celery

# Flask app setup
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Celery configuration
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
app.config["CELERY_BROKER_URL"] = redis_url
app.config["CELERY_RESULT_BACKEND"] = redis_url

# Initialize Celery (only for task triggering and status checking)
celery = Celery(
    "notification",
    broker=app.config["CELERY_BROKER_URL"],
    backend=app.config["CELERY_RESULT_BACKEND"],
)

# Define task signature (must match worker definition)
send_email_task = celery.signature("worker.send_email_task")


@app.route("/health", methods=["GET"])
def health_check() -> Any:
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "notification-api"})


@app.route("/send-email", methods=["POST"])
def send_email() -> Any:
    """
    REST API endpoint to send email
    Expected JSON payload:
    {
        "to": "recipient@example.com",
        "subject": "Email Subject",
        "body": "Email body content",
        "from": "sender@example.com" (optional)
    }
    """
    try:
        data = request.get_json()

        # Validate required fields
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        required_fields = ["to", "subject", "body"]
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return jsonify(
                {"error": f"Missing required fields: {', '.join(missing_fields)}"}
            ), 400

        to_email = data["to"]
        subject = data["subject"]
        body = data["body"]
        from_email = data.get("from", "noreply@example.com")

        # Queue email sending task
        task = celery.send_task(
            "worker.send_email_task", args=[to_email, subject, body, from_email]
        )

        logger.info(f"Email queued for sending to {to_email} with subject '{subject}'")

        return jsonify(
            {
                "message": "Email queued for sending",
                "task_id": task.id,
                "to": to_email,
                "subject": subject,
            }
        ), 202

    except Exception as e:
        logger.error(f"Error processing email request: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/task-status/<task_id>", methods=["GET"])
def get_task_status(task_id: str) -> Any:
    """Get the status of a Celery task"""
    try:
        task = celery.AsyncResult(task_id)

        if task.state == "PENDING":
            response = {
                "state": task.state,
                "status": "Task is waiting to be processed",
            }
        elif task.state == "SUCCESS":
            response = {"state": task.state, "result": task.result}
        elif task.state == "FAILURE":
            response = {"state": task.state, "error": str(task.info)}
        else:
            response = {"state": task.state, "status": "Task is being processed"}

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error getting task status for {task_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Run Flask app
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=8000, debug=debug_mode)
