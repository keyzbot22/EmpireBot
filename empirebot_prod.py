from flask import Flask, request, jsonify
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import json
import datetime

app = Flask(__name__)

@app.route("/")
def home():
    return "EmpireBot is running."

@app.route("/proofs/upload", methods=["POST"])
def upload_proof():
    try:
        # Load Google credentials from the environment variable
        google_creds = os.getenv("GOOGLE_CREDS")
        if not google_creds:
            return jsonify({"error": "GOOGLE_CREDS not set in environment"}), 400

        creds_dict = json.loads(google_creds)
        creds = Credentials.from_authorized_user_info(creds_dict)

        # Build the Drive API client
        service = build("drive", "v3", credentials=creds)

        # Create the proof file
        filename = f"proof-{datetime.datetime.now().strftime('%Y-%m-%d')}.txt"
        filepath = os.path.join("proofs", filename)
        os.makedirs("proofs", exist_ok=True)

        with open(filepath, "w") as f:
            f.write("EmpireBot Proof of Execution\nTime: " + datetime.datetime.now().isoformat())

        # Prepare the file upload to Google Drive
        folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        if not folder_id:
            return jsonify({"error": "GOOGLE_DRIVE_FOLDER_ID not set in environment"}), 400

        file_metadata = {"name": filename, "parents": [folder_id]}
        media = MediaFileUpload(filepath, mimetype="text/plain")

        uploaded_file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()

        return jsonify({"status": "uploaded", "file_id": uploaded_file.get("id")})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run()

