import os
from concurrent import futures

import grpc

from music_service.config import GRPC_PORT
from music_service.domain.music_store import DomainError, MusicStore
from music_service.generated import music_pb2, music_pb2_grpc


store = MusicStore()
GRPC_MAX_WORKERS = int(os.getenv("GRPC_MAX_WORKERS", "512"))
GRPC_MAX_CONCURRENT_STREAMS = int(os.getenv("GRPC_MAX_CONCURRENT_STREAMS", "2048"))


def user_message(user):
    return music_pb2.User(id=user["id"], name=user["name"], email=user["email"])


def song_message(song):
    return music_pb2.Song(
        id=song["id"],
        title=song["title"],
        artist=song["artist"],
        album=song["album"],
        durationSeconds=song["durationSeconds"],
    )


def playlist_message(playlist):
    return music_pb2.Playlist(
        id=playlist["id"],
        userId=playlist["userId"],
        name=playlist["name"],
        songIds=playlist["songIds"],
    )


def mutation_result(result):
    return music_pb2.MutationResult(ok=bool(result.get("ok")))


def users_response(users):
    response = music_pb2.UsersResponse()
    response.users.extend(user_message(user) for user in users)
    return response


def songs_response(songs):
    response = music_pb2.SongsResponse()
    response.songs.extend(song_message(song) for song in songs)
    return response


def playlists_response(playlists):
    response = music_pb2.PlaylistsResponse()
    response.playlists.extend(playlist_message(playlist) for playlist in playlists)
    return response


def compact(data):
    return {
        key: value
        for key, value in data.items()
        if value not in ("", 0, [], None)
    }


def user_input(request):
    return {"name": request.name, "email": request.email}


def song_input(request):
    return {
        "title": request.title,
        "artist": request.artist,
        "album": request.album,
        "durationSeconds": request.durationSeconds,
    }


def playlist_input(request):
    return {
        "userId": request.userId,
        "name": request.name,
        "songIds": list(request.songIds),
    }


def user_patch(request):
    return compact({"name": request.name, "email": request.email})


def song_patch(request):
    return compact({
        "title": request.title,
        "artist": request.artist,
        "album": request.album,
        "durationSeconds": request.durationSeconds,
    })


def playlist_patch(request):
    return compact({
        "userId": request.userId,
        "name": request.name,
        "songIds": list(request.songIds),
    })


def grpc_error(error, context):
    if isinstance(error, DomainError):
        context.set_code(grpc.StatusCode.NOT_FOUND if error.status == 404 else grpc.StatusCode.INVALID_ARGUMENT)
    else:
        context.set_code(grpc.StatusCode.INTERNAL)
    context.set_details(str(error) or "Erro inesperado")


class MusicStreamingService(music_pb2_grpc.MusicStreamingServicer):
    def Reset(self, request, context):
        try:
            return mutation_result(store.reset())
        except Exception as error:
            grpc_error(error, context)
            return music_pb2.MutationResult()

    def ListUsers(self, request, context):
        try:
            return users_response(store.list_users())
        except Exception as error:
            grpc_error(error, context)
            return music_pb2.UsersResponse()

    def GetUser(self, request, context):
        try:
            return user_message(store.get_user(request.id))
        except Exception as error:
            grpc_error(error, context)
            return music_pb2.User()

    def CreateUser(self, request, context):
        try:
            return user_message(store.create_user(user_input(request)))
        except Exception as error:
            grpc_error(error, context)
            return music_pb2.User()

    def UpdateUser(self, request, context):
        try:
            return user_message(store.update_user(request.id, user_patch(request.user)))
        except Exception as error:
            grpc_error(error, context)
            return music_pb2.User()

    def DeleteUser(self, request, context):
        try:
            return mutation_result(store.delete_user(request.id))
        except Exception as error:
            grpc_error(error, context)
            return music_pb2.MutationResult()

    def ListSongs(self, request, context):
        try:
            return songs_response(store.list_songs())
        except Exception as error:
            grpc_error(error, context)
            return music_pb2.SongsResponse()

    def GetSong(self, request, context):
        try:
            return song_message(store.get_song(request.id))
        except Exception as error:
            grpc_error(error, context)
            return music_pb2.Song()

    def CreateSong(self, request, context):
        try:
            return song_message(store.create_song(song_input(request)))
        except Exception as error:
            grpc_error(error, context)
            return music_pb2.Song()

    def UpdateSong(self, request, context):
        try:
            return song_message(store.update_song(request.id, song_patch(request.song)))
        except Exception as error:
            grpc_error(error, context)
            return music_pb2.Song()

    def DeleteSong(self, request, context):
        try:
            return mutation_result(store.delete_song(request.id))
        except Exception as error:
            grpc_error(error, context)
            return music_pb2.MutationResult()

    def ListPlaylists(self, request, context):
        try:
            filters = compact({"userId": request.userId, "songId": request.songId})
            return playlists_response(store.list_playlists(filters))
        except Exception as error:
            grpc_error(error, context)
            return music_pb2.PlaylistsResponse()

    def GetPlaylist(self, request, context):
        try:
            return playlist_message(store.get_playlist(request.id))
        except Exception as error:
            grpc_error(error, context)
            return music_pb2.Playlist()

    def CreatePlaylist(self, request, context):
        try:
            return playlist_message(store.create_playlist(playlist_input(request)))
        except Exception as error:
            grpc_error(error, context)
            return music_pb2.Playlist()

    def UpdatePlaylist(self, request, context):
        try:
            return playlist_message(store.update_playlist(request.id, playlist_patch(request.playlist)))
        except Exception as error:
            grpc_error(error, context)
            return music_pb2.Playlist()

    def DeletePlaylist(self, request, context):
        try:
            return mutation_result(store.delete_playlist(request.id))
        except Exception as error:
            grpc_error(error, context)
            return music_pb2.MutationResult()

    def ListUserPlaylists(self, request, context):
        try:
            return playlists_response(store.list_user_playlists(request.userId))
        except Exception as error:
            grpc_error(error, context)
            return music_pb2.PlaylistsResponse()

    def ListPlaylistSongs(self, request, context):
        try:
            return songs_response(store.list_playlist_songs(request.playlistId))
        except Exception as error:
            grpc_error(error, context)
            return music_pb2.SongsResponse()

    def ListSongPlaylists(self, request, context):
        try:
            return playlists_response(store.list_song_playlists(request.songId))
        except Exception as error:
            grpc_error(error, context)
            return music_pb2.PlaylistsResponse()


def create_server():
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=GRPC_MAX_WORKERS),
        options=[
            ("grpc.max_concurrent_streams", GRPC_MAX_CONCURRENT_STREAMS),
            ("grpc.so_reuseport", 1),
        ],
    )
    music_pb2_grpc.add_MusicStreamingServicer_to_server(MusicStreamingService(), server)
    bound_port = server.add_insecure_port(f"0.0.0.0:{GRPC_PORT}")
    if bound_port == 0:
        raise RuntimeError(f"Nao foi possivel abrir a porta gRPC {GRPC_PORT}")
    return server


def main():
    server = create_server()
    server.start()
    print(f"gRPC ouvindo em 0.0.0.0:{GRPC_PORT} | workers={GRPC_MAX_WORKERS} | max_streams={GRPC_MAX_CONCURRENT_STREAMS}", flush=True)
    server.wait_for_termination()


if __name__ == "__main__":
    main()
