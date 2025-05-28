import json
import os
import base64

import requests
from dotenv import load_dotenv
from requests import post, get
from flask import Flask, request, redirect, jsonify, session
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=[
    "http://localhost:5173",
])

app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
redirect_uri = "https://spotify-project-vb7f.onrender.com/callback"

scopes = "user-read-private user-read-email user-read-recently-played user-top-read user-read-playback-state"


@app.route("/")
def login():
    auth_url = (
        "https://accounts.spotify.com/authorize"
        f"?client_id={client_id}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scopes}"
    )
    return redirect(auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "No code provided.", 400

    token_url = "https://accounts.spotify.com/api/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    res = requests.post(token_url, headers=headers, data=data)
    token_info = res.json()

    if "access_token" not in token_info:
        return f"Error getting access token: {token_info}", 400

    access_token = token_info["access_token"]
    session['access_token'] = access_token  # Store token in session

    # Redirect to Vue frontend
    return redirect("http://localhost:5173")  # Replace with actual frontend URL

@app.route("/api/user")
def api_user():
    access_token = session.get('access_token')
    if not access_token:
        return jsonify({"error": "No access token. Please log in."}), 401

    user_info = get_user_data(access_token)
    recently_played = get_recently_played(access_token)

    return jsonify({
        "user": user_info,
        "recently_played": [item["track"] for item in recently_played["items"]] if recently_played and "items" in recently_played else []
    })

def get_auth_header(token):
    return {"Authorization": "Bearer " + token}

def get_user_data(token):
    url = "https://api.spotify.com/v1/me"
    headers = get_auth_header(token)
    result = get(url, headers=headers)
    return json.loads(result.content)

def get_token():
    auth_string = client_id + ":" + client_secret
    auth_bytes = auth_string.encode('utf-8')
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {"grant_type": "client_credentials"}
    result = post(url, headers=headers, data=data)
    json_result = json.loads(result.text)
    token = json_result["access_token"]
    return token

def search_for_artist(token, artist_name):
    url = "https://api.spotify.com/v1/search"
    headers = get_auth_header(token)
    query = f"?q={artist_name}&type=artist&limit=1"

    query_url = url + query
    result = get(query_url, headers=headers)
    json_result = json.loads(result.content)["artists"]["items"]
    if len(json_result) == 0:
        print("Artist not found")
        return None
    return json_result[0]

def get_songs_by_artist(token, artist_id):
    url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?country=US"
    headers = get_auth_header(token)
    result = get(url, headers=headers)
    json_result = json.loads(result.content)["tracks"]
    return json_result

def get_recently_played(token):
    url = "https://api.spotify.com/v1/me/player/recently-played"
    headers = get_auth_header(token)
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print("Error fetching recently played:", response.json())
        return None
    return response.json()


# token = get_token()
# result = search_for_artist(token, "Magdalena Bay")
# artist_id = result["id"]
# songs = get_songs_by_artist(token, artist_id)

# for idx, song in enumerate(songs):
#     print(f"{idx + 1}. {song['name']}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Default to 8080 if PORT not set
    app.run(host="0.0.0.0", port=port)