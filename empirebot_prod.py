import os
import json
import base64
import hmac
import hashlib
from datetime import datetime
from flask import Flask, request, jsonify
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

app = Flask(__name__)

def generate_md5(file_path):
    with open(file_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def store_proof(proof):
    with open("drive_proofs.jsonl", "a") as f:
        f.write(json.dumps(proof) + "\n")

def upload_to_drive(file_path, folder_id=None):
    try:
        creds_json = os.getenv("GOOGLE_CREDS")
        if not creds_json:
            raise ValueError("Missing GOOGLE_CREDS environment variable")

        creds_data = json.loads(creds_json)
        creds = Credentials.from_authorized_user_info(creds_data, ['https://www.googleapis.com/auth/drive'])

        service = build('drive', 'v3', credentials=creds)

        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [folder_id] if folder_id else []
        }
        media = MediaFileUpload(file_path)
        uploaded = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        file_id = uploaded.get('id')
        proof = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "file_id": file_id,
            "file_name": os.path.basename(file_path),
            "folder_id": folder_id,
            "md5_hash": generate_md5(file_path),
            "screenshot_url": None
        }
        store_proof(proof)
        return file_id, proof

    except Exception as e:
        raise RuntimeError(f"Google Drive upload failed: {e}")

@app.route("/")
def home():
    return "EmpireBot is online."

@app.route("/upload/manual", methods=["POST"])
def manual_upload():
    try:
        file_path = "test_upload.txt"
        folder_id = os.getenv("DRIVE_TEST_FOLDER_ID")
        file_id, proof = upload_to_drive(file_path, folder_id)
        return jsonify({"status": "uploaded", "file_id": file_id, "proof": proof})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/proofs/latest")
def latest_proof():
    try:
        with open("drive_proofs.jsonl", "r") as f:
            lines = f.readlines()
            if lines:
                return jsonify(json.loads(lines[-1]))
            return jsonify({"status": "No proofs found"}), 404
    except FileNotFoundError:
        return jsonify({"error": "Proof log not initialized yet"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
