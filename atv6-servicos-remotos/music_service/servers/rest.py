from fastapi import Body, FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from music_service.config import REST_PORT
from music_service.domain.music_store import DomainError, MusicStore, plain_error


store = MusicStore()
app = FastAPI(title="Music Streaming REST")


@app.exception_handler(DomainError)
async def domain_error_handler(_request: Request, error: DomainError):
    return JSONResponse(status_code=error.status, content=plain_error(error))


@app.get("/health")
def health():
    return {"ok": True, "technology": "REST"}


@app.post("/reset")
def reset():
    return store.reset()


@app.get("/users")
def list_users():
    return store.list_users()


@app.post("/users", status_code=201)
def create_user(payload: dict = Body(default_factory=dict)):
    return store.create_user(payload)


@app.get("/users/{user_id}/playlists")
def list_user_playlists(user_id: str):
    return store.list_user_playlists(user_id)


@app.get("/users/{user_id}")
def get_user(user_id: str):
    return store.get_user(user_id)


@app.put("/users/{user_id}")
def update_user(user_id: str, payload: dict = Body(default_factory=dict)):
    return store.update_user(user_id, payload)


@app.delete("/users/{user_id}")
def delete_user(user_id: str):
    return store.delete_user(user_id)


@app.get("/songs")
def list_songs():
    return store.list_songs()


@app.post("/songs", status_code=201)
def create_song(payload: dict = Body(default_factory=dict)):
    return store.create_song(payload)


@app.get("/songs/{song_id}/playlists")
def list_song_playlists(song_id: str):
    return store.list_song_playlists(song_id)


@app.get("/songs/{song_id}")
def get_song(song_id: str):
    return store.get_song(song_id)


@app.put("/songs/{song_id}")
def update_song(song_id: str, payload: dict = Body(default_factory=dict)):
    return store.update_song(song_id, payload)


@app.delete("/songs/{song_id}")
def delete_song(song_id: str):
    return store.delete_song(song_id)


@app.get("/playlists")
def list_playlists(userId: str | None = None, songId: str | None = None):
    return store.list_playlists({"userId": userId, "songId": songId})


@app.post("/playlists", status_code=201)
def create_playlist(payload: dict = Body(default_factory=dict)):
    return store.create_playlist(payload)


@app.get("/playlists/{playlist_id}/songs")
def list_playlist_songs(playlist_id: str):
    return store.list_playlist_songs(playlist_id)


@app.get("/playlists/{playlist_id}")
def get_playlist(playlist_id: str):
    return store.get_playlist(playlist_id)


@app.put("/playlists/{playlist_id}")
def update_playlist(playlist_id: str, payload: dict = Body(default_factory=dict)):
    return store.update_playlist(playlist_id, payload)


@app.delete("/playlists/{playlist_id}")
def delete_playlist(playlist_id: str):
    return store.delete_playlist(playlist_id)


def main():
    uvicorn.run(app, host="0.0.0.0", port=REST_PORT)


if __name__ == "__main__":
    main()
