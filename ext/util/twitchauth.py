import time
from credentials import TWITCH_ID, TWITCH_SECRET

async def twitch_auth(db, http_client):
    """Generic function to get Twitch auth headers for IGDB"""

    await db.execute("""CREATE TABLE IF NOT EXISTS twitch_auth
        (token text, expiry integer)""")

    try:
        token, expiry = await db.fetchrow("""SELECT token, expiry from twitch_auth
            ORDER BY expiry DESC""")
    except:
        token, expiry = 0, 0

    if not token or (int(time.time()) + 120) > expiry:
        params = {
            "client_id": TWITCH_ID,
            "client_secret": TWITCH_SECRET,
            "grant_type": "client_credentials"
        }

        r = await http_client.post(
            "https://id.twitch.tv/oauth2/token", params=params)
        js = r.json()

        await db.execute("INSERT INTO twitch_auth VALUES ($1, $2)",
            js["access_token"], (int(time.time())+js["expires_in"]))

    headers = {
        "client-id": TWITCH_ID,
        "Authorization": f"Bearer {token}"
    }

    return headers
