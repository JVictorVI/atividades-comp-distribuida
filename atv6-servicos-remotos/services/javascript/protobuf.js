export function encodeVarint(value) {
  let current = Number(value);
  const bytes = [];
  while (true) {
    const byte = current & 0x7f;
    current >>>= 7;
    if (current) {
      bytes.push(byte | 0x80);
    } else {
      bytes.push(byte);
      return Buffer.from(bytes);
    }
  }
}

export function decodeVarint(buffer, startPosition = 0) {
  let shift = 0;
  let result = 0;
  let position = startPosition;

  while (position < buffer.length) {
    const byte = buffer[position];
    position += 1;
    result |= (byte & 0x7f) << shift;
    if ((byte & 0x80) === 0) {
      return [result, position];
    }
    shift += 7;
  }

  throw new Error("Varint incompleto");
}

export function parseFields(buffer) {
  const fields = new Map();
  let position = 0;

  while (position < buffer.length) {
    const [tag, nextPosition] = decodeVarint(buffer, position);
    position = nextPosition;
    const fieldNumber = tag >> 3;
    const wireType = tag & 0x07;
    let value;

    if (wireType === 0) {
      [value, position] = decodeVarint(buffer, position);
    } else if (wireType === 2) {
      const [length, afterLength] = decodeVarint(buffer, position);
      position = afterLength;
      value = buffer.subarray(position, position + length);
      position += length;
    } else {
      throw new Error(`Wire type nao suportado: ${wireType}`);
    }

    if (!fields.has(fieldNumber)) {
      fields.set(fieldNumber, []);
    }
    fields.get(fieldNumber).push(value);
  }

  return fields;
}

export function firstString(fields, number, defaultValue = "") {
  const values = fields.get(number);
  return values && values.length ? values[0].toString("utf8") : defaultValue;
}

export function firstInt(fields, number, defaultValue = 0) {
  const values = fields.get(number);
  return values && values.length ? Number(values[0]) : defaultValue;
}

export function stringField(number, value) {
  const data = Buffer.from(String(value), "utf8");
  return Buffer.concat([
    encodeVarint((number << 3) | 2),
    encodeVarint(data.length),
    data
  ]);
}

export function intField(number, value) {
  return Buffer.concat([
    encodeVarint((number << 3) | 0),
    encodeVarint(Number(value))
  ]);
}

export function boolField(number, value) {
  return intField(number, value ? 1 : 0);
}

export function messageField(number, value) {
  return Buffer.concat([
    encodeVarint((number << 3) | 2),
    encodeVarint(value.length),
    value
  ]);
}

export function encodeUser(user) {
  return Buffer.concat([
    stringField(1, user.id),
    stringField(2, user.name),
    stringField(3, user.email)
  ]);
}

export function encodeSong(song) {
  return Buffer.concat([
    stringField(1, song.id),
    stringField(2, song.title),
    stringField(3, song.artist),
    stringField(4, song.album),
    intField(5, song.durationSeconds)
  ]);
}

export function encodePlaylist(playlist) {
  return Buffer.concat([
    stringField(1, playlist.id),
    stringField(2, playlist.userId),
    stringField(3, playlist.name),
    ...playlist.songIds.map((songId) => stringField(4, songId))
  ]);
}

export function usersResponse(users) {
  return Buffer.concat(users.map((user) => messageField(1, encodeUser(user))));
}

export function songsResponse(songs) {
  return Buffer.concat(songs.map((song) => messageField(1, encodeSong(song))));
}

export function playlistsResponse(playlists) {
  return Buffer.concat(playlists.map((playlist) => messageField(1, encodePlaylist(playlist))));
}

export function mutationResult(result) {
  return boolField(1, Boolean(result.ok));
}

export function decodeIdRequest(request) {
  return firstString(parseFields(request), 1);
}

export function decodeUserInput(request) {
  const fields = parseFields(request);
  return {
    name: firstString(fields, 1),
    email: firstString(fields, 2)
  };
}

export function decodeSongInput(request) {
  const fields = parseFields(request);
  return {
    title: firstString(fields, 1),
    artist: firstString(fields, 2),
    album: firstString(fields, 3),
    durationSeconds: firstInt(fields, 4)
  };
}

export function decodePlaylistInput(request) {
  const fields = parseFields(request);
  return {
    userId: firstString(fields, 1),
    name: firstString(fields, 2),
    songIds: (fields.get(3) || []).map((value) => value.toString("utf8"))
  };
}

function compact(data) {
  return Object.fromEntries(
    Object.entries(data).filter(([, value]) => {
      if (Array.isArray(value)) {
        return value.length > 0;
      }
      return value !== "" && value !== 0 && value !== null && value !== undefined;
    })
  );
}

export function decodeUpdateUser(request) {
  const fields = parseFields(request);
  const patchFields = parseFields((fields.get(2) || [Buffer.alloc(0)])[0]);
  return [
    firstString(fields, 1),
    compact({
      name: firstString(patchFields, 1),
      email: firstString(patchFields, 2)
    })
  ];
}

export function decodeUpdateSong(request) {
  const fields = parseFields(request);
  const patchFields = parseFields((fields.get(2) || [Buffer.alloc(0)])[0]);
  return [
    firstString(fields, 1),
    compact({
      title: firstString(patchFields, 1),
      artist: firstString(patchFields, 2),
      album: firstString(patchFields, 3),
      durationSeconds: firstInt(patchFields, 4)
    })
  ];
}

export function decodeUpdatePlaylist(request) {
  const fields = parseFields(request);
  const patchFields = parseFields((fields.get(2) || [Buffer.alloc(0)])[0]);
  return [
    firstString(fields, 1),
    compact({
      userId: firstString(patchFields, 1),
      name: firstString(patchFields, 2),
      songIds: (patchFields.get(3) || []).map((value) => value.toString("utf8"))
    })
  ];
}

export function decodePlaylistFilter(request) {
  const fields = parseFields(request);
  return compact({
    userId: firstString(fields, 1),
    songId: firstString(fields, 2)
  });
}
