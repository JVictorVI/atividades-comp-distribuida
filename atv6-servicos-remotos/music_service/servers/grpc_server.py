from concurrent import futures

import grpc

from music_service.config import GRPC_PORT
from music_service.domain.music_store import DomainError, MusicStore


store = MusicStore()


def encode_varint(value: int) -> bytes:
    encoded = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            encoded.append(byte | 0x80)
        else:
            encoded.append(byte)
            return bytes(encoded)


def decode_varint(buffer: bytes, position: int):
    shift = 0
    result = 0
    while True:
        byte = buffer[position]
        position += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, position
        shift += 7


def parse_fields(buffer: bytes):
    fields = {}
    position = 0
    while position < len(buffer):
        tag, position = decode_varint(buffer, position)
        field_number = tag >> 3
        wire_type = tag & 0x07

        if wire_type == 0:
            value, position = decode_varint(buffer, position)
        elif wire_type == 2:
            length, position = decode_varint(buffer, position)
            value = buffer[position: position + length]
            position += length
        else:
            raise ValueError(f"Wire type não suportado: {wire_type}")

        fields.setdefault(field_number, []).append(value)
    return fields


def first_string(fields, number, default=""):
    values = fields.get(number)
    return values[0].decode("utf-8") if values else default


def first_int(fields, number, default=0):
    values = fields.get(number)
    return int(values[0]) if values else default


def string_field(number: int, value: str) -> bytes:
    data = str(value).encode("utf-8")
    return encode_varint((number << 3) | 2) + encode_varint(len(data)) + data


def int_field(number: int, value: int) -> bytes:
    return encode_varint((number << 3) | 0) + encode_varint(int(value))


def bool_field(number: int, value: bool) -> bytes:
    return int_field(number, 1 if value else 0)


def message_field(number: int, value: bytes) -> bytes:
    return encode_varint((number << 3) | 2) + encode_varint(len(value)) + value


def encode_user(user) -> bytes:
    return b"".join([
        string_field(1, user["id"]),
        string_field(2, user["name"]),
        string_field(3, user["email"]),
    ])


def encode_song(song) -> bytes:
    return b"".join([
        string_field(1, song["id"]),
        string_field(2, song["title"]),
        string_field(3, song["artist"]),
        string_field(4, song["album"]),
        int_field(5, song["durationSeconds"]),
    ])


def encode_playlist(playlist) -> bytes:
    payload = [
        string_field(1, playlist["id"]),
        string_field(2, playlist["userId"]),
        string_field(3, playlist["name"]),
    ]
    payload.extend(string_field(4, song_id) for song_id in playlist["songIds"])
    return b"".join(payload)


def users_response(users) -> bytes:
    return b"".join(message_field(1, encode_user(user)) for user in users)


def songs_response(songs) -> bytes:
    return b"".join(message_field(1, encode_song(song)) for song in songs)


def playlists_response(playlists) -> bytes:
    return b"".join(message_field(1, encode_playlist(playlist)) for playlist in playlists)


def mutation_result(result) -> bytes:
    return bool_field(1, bool(result.get("ok")))


def decode_id_request(request: bytes):
    return first_string(parse_fields(request), 1)


def decode_user_input(request: bytes):
    fields = parse_fields(request)
    return {"name": first_string(fields, 1), "email": first_string(fields, 2)}


def decode_song_input(request: bytes):
    fields = parse_fields(request)
    return {
        "title": first_string(fields, 1),
        "artist": first_string(fields, 2),
        "album": first_string(fields, 3),
        "durationSeconds": first_int(fields, 4),
    }


def decode_playlist_input(request: bytes):
    fields = parse_fields(request)
    return {
        "userId": first_string(fields, 1),
        "name": first_string(fields, 2),
        "songIds": [value.decode("utf-8") for value in fields.get(3, [])],
    }


def compact(data):
    return {key: value for key, value in data.items() if value not in ("", 0, [], None)}


def decode_update_user(request: bytes):
    fields = parse_fields(request)
    patch_fields = parse_fields(fields.get(2, [b""])[0])
    return first_string(fields, 1), compact({
        "name": first_string(patch_fields, 1),
        "email": first_string(patch_fields, 2),
    })


def decode_update_song(request: bytes):
    fields = parse_fields(request)
    patch_fields = parse_fields(fields.get(2, [b""])[0])
    return first_string(fields, 1), compact({
        "title": first_string(patch_fields, 1),
        "artist": first_string(patch_fields, 2),
        "album": first_string(patch_fields, 3),
        "durationSeconds": first_int(patch_fields, 4),
    })


def decode_update_playlist(request: bytes):
    fields = parse_fields(request)
    patch_fields = parse_fields(fields.get(2, [b""])[0])
    return first_string(fields, 1), compact({
        "userId": first_string(patch_fields, 1),
        "name": first_string(patch_fields, 2),
        "songIds": [value.decode("utf-8") for value in patch_fields.get(3, [])],
    })


def decode_playlist_filter(request: bytes):
    fields = parse_fields(request)
    return compact({"userId": first_string(fields, 1), "songId": first_string(fields, 2)})


def unary(handler, encoder):
    def execute(request: bytes, context):
        try:
            return encoder(handler(request))
        except DomainError as error:
            context.set_code(grpc.StatusCode.NOT_FOUND if error.status == 404 else grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(error))
            return b""
        except Exception as error:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(error))
            return b""

    return grpc.unary_unary_rpc_method_handler(
        execute,
        request_deserializer=lambda data: data,
        response_serializer=lambda data: data,
    )


def create_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=64))
    handlers = {
        "Reset": unary(lambda _request: store.reset(), mutation_result),
        "ListUsers": unary(lambda _request: store.list_users(), users_response),
        "GetUser": unary(lambda request: store.get_user(decode_id_request(request)), encode_user),
        "CreateUser": unary(lambda request: store.create_user(decode_user_input(request)), encode_user),
        "UpdateUser": unary(lambda request: store.update_user(*decode_update_user(request)), encode_user),
        "DeleteUser": unary(lambda request: store.delete_user(decode_id_request(request)), mutation_result),
        "ListSongs": unary(lambda _request: store.list_songs(), songs_response),
        "GetSong": unary(lambda request: store.get_song(decode_id_request(request)), encode_song),
        "CreateSong": unary(lambda request: store.create_song(decode_song_input(request)), encode_song),
        "UpdateSong": unary(lambda request: store.update_song(*decode_update_song(request)), encode_song),
        "DeleteSong": unary(lambda request: store.delete_song(decode_id_request(request)), mutation_result),
        "ListPlaylists": unary(lambda request: store.list_playlists(decode_playlist_filter(request)), playlists_response),
        "GetPlaylist": unary(lambda request: store.get_playlist(decode_id_request(request)), encode_playlist),
        "CreatePlaylist": unary(lambda request: store.create_playlist(decode_playlist_input(request)), encode_playlist),
        "UpdatePlaylist": unary(lambda request: store.update_playlist(*decode_update_playlist(request)), encode_playlist),
        "DeletePlaylist": unary(lambda request: store.delete_playlist(decode_id_request(request)), mutation_result),
        "ListUserPlaylists": unary(
            lambda request: store.list_user_playlists(first_string(parse_fields(request), 1)),
            playlists_response,
        ),
        "ListPlaylistSongs": unary(
            lambda request: store.list_playlist_songs(first_string(parse_fields(request), 1)),
            songs_response,
        ),
        "ListSongPlaylists": unary(
            lambda request: store.list_song_playlists(first_string(parse_fields(request), 1)),
            playlists_response,
        ),
    }
    service = grpc.method_handlers_generic_handler("music.MusicStreaming", handlers)
    server.add_generic_rpc_handlers((service,))
    bound_port = server.add_insecure_port(f"0.0.0.0:{GRPC_PORT}")
    if bound_port == 0:
        raise RuntimeError(f"Não foi possível abrir a porta gRPC {GRPC_PORT}")
    return server


def main():
    server = create_server()
    server.start()
    print(f"gRPC ouvindo em 0.0.0.0:{GRPC_PORT}", flush=True)
    server.wait_for_termination()


if __name__ == "__main__":
    main()
