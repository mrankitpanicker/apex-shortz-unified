import os
import sys
import httplib2
from pathlib import Path

# Core Google API imports
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Core Google Auth imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Import configurations (CLIENT_SECRET_FILE, TOKEN_FILE, SCOPES)
import config


# ================================================================
# 🪄 YOUTUBE AUTHENTICATION FUNCTIONS
# ================================================================

def get_credentials():
    """Load or generate OAuth2 credentials (saved to token.json)."""
    creds = None

    # Use configuration variables
    TOKEN_FILE = config.TOKEN_FILE
    SCOPES = config.SCOPES
    CLIENT_SECRETS_FILE = config.CLIENT_SECRET_FILE # Renamed to use config file name

    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            print(f"🔑 Loaded existing token from {TOKEN_FILE}")
        except Exception as e:
            print(f"⚠️ Failed to load saved token: {e}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("🔁 Token refreshed successfully.")
            except Exception as e:
                print(f"⚠️ Refresh failed: {e}")
                creds = None

        if not creds:
            print("🌐 Running browser login to get new credentials...")
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES
            )
            creds = flow.run_local_server(
                port=0, access_type="offline", prompt="consent"
            )

        # Save token
        try:
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            print(f"💾 Saved credentials to {TOKEN_FILE}")
        except Exception as e:
            print(f"❌ Failed to save token.json: {e}")

    if not creds:
        print("🛑 Critical: Failed to obtain valid credentials.")
        sys.exit(1)

    return creds


def get_authenticated_service():
    """Returns an authenticated YouTube service object."""
    creds = get_credentials()
    return build("youtube", "v3", credentials=creds)


def upload_to_youtube(
    video_path, title, description, tags, privacy="public", test_mode=False
):
    """
    Uploads a video to YouTube. Skips upload and prints metadata if test_mode=True.
    """
    if test_mode:
        print("\n⚙️  TEST MODE ACTIVE: Skipping actual YouTube upload.")
        print("--- YouTube Metadata Ready ---")
        print(f"Title: {title}")
        print(f"Path: {video_path}")
        print(f"Privacy: {privacy}")
        print(f"Tags ({len(tags)}): {', '.join(tags[:5])}...")
        print("--- End Metadata ---")
        return True

    try:
        youtube = get_authenticated_service()

        print("\n🚀 Uploading to YouTube (resumable, 30 min timeout)...")

        # 🔹 Use resumable upload
        media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)

        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "categoryId": "22",  # People & Blogs
                },
                "status": {"privacyStatus": privacy},
            },
            media_body=media,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"⬆️  Upload progress: {int(status.progress() * 100)}%")

        print(
            f"✅ Uploaded successfully! Video link: https://youtu.be/{response['id']}"
        )
        return True

    except HttpError as e:
        print(f"❌ Upload failed (HTTP Error): {e}")
        return False
    except Exception as e:
        print(f"⚠️ Unexpected error during upload: {e}")
        return False