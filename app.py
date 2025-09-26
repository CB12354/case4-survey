from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from pydantic import ValidationError
from models import SurveySubmission, StoredSurveyRecord
from storage import append_json_line
import hashlib

app = Flask(__name__)
# Allow cross-origin requests so the static HTML can POST from localhost or file://
CORS(app, resources={r"/v1/*": {"origins": "*"}})

@app.route("/ping", methods=["GET"])
def ping():
    """Simple health check endpoint."""
    return jsonify({
        "status": "ok",
        "message": "API is alive",
        "utc_time": datetime.now(timezone.utc).isoformat()
    })

@app.post("/v1/survey")
def submit_survey():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "invalid_json", "detail": "Body must be application/json"}), 400

    try:
        submission = SurveySubmission(**payload)
    except ValidationError as ve:
        return jsonify({"error": "validation_error", "detail": ve.errors()}), 422

    subdict = submission.dict()
    now = datetime.now(timezone.utc)
    record = StoredSurveyRecord(
        **subdict,
        received_at=now,
        ip=request.headers.get("X-Forwarded-For", request.remote_addr or ""),
        user_agent=request.headers.get("User-Agent"),
        submission_id=hashlib.sha256((subdict['email']+str(now)).encode('utf-8')).hexdigest()
    )
    recdict = record.dict()
    recdict['email'] = hashlib.sha256(recdict['email'].encode('utf-8')).hexdigest()
    recdict['age'] = hashlib.sha256(str(recdict['age']).encode('utf-8')).hexdigest()
    append_json_line(recdict)
    return jsonify({"status": "ok"}), 201

if __name__ == "__main__":
    app.run(port=0, debug=True)
