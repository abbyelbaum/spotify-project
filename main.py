import json
import os
import base64

import requests
from dotenv import load_dotenv
from requests import post, get
from flask import Flask, request, redirect

load_dotenv()

app = Flask(__name__)

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
redirect_uri = "https://bffb-2607-fb91-db0-8951-111f-e121-59b4-a9e8.ngrok-free.app/callback"

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
        "redirect_uri": redirect_uri,  # 👈 Key fixed
        "client_id": client_id,
        "client_secret": client_secret,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    res = requests.post(token_url, headers=headers, data=data)
    token_info = res.json()

    if "access_token" not in token_info:
        return f"Error getting access token: {token_info}", 400

    access_token = token_info["access_token"]

    user_info = get_user_data(access_token)
    recently_played = get_recently_played(access_token)

    html = f"<h1>Welcome, {user_info['display_name']}</h1>"
    html += f"<p>Email: {user_info['email']}</p>"

    if recently_played and "items" in recently_played:
        html += "<h2>Recently Played Tracks:</h2><ul>"
        for item in recently_played["items"]:
            track = item["track"]
            html += f"<li>{track['name']} by {', '.join([artist['name'] for artist in track['artists']])}</li>"
        html += "</ul>"
    else:
        html += "<h2>No recently played tracks found.</h2>"

    return html

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
    app.run(port=8080)
    print(get_user_data(get_token()))
