export class DomainError extends Error {
  constructor(status, code, message) {
    super(message);
    this.name = "DomainError";
    this.status = status;
    this.code = code;
  }
}

const INITIAL_USER_COUNT = 300;
const INITIAL_SONG_COUNT = 500;
const INITIAL_PLAYLIST_COUNT = 400;
const FEATURED_PLAYLIST_SONG_COUNT = 300;
const TARGET_USER_PLAYLIST_COUNT = 300;
const TARGET_SONG_PLAYLIST_COUNT = 300;

const BASE_DATA = {
  users: [
    { id: "u1", name: "Ana Costa", email: "ana@example.com" },
    { id: "u2", name: "Bruno Lima", email: "bruno@example.com" },
    { id: "u3", name: "Carla Souza", email: "carla@example.com" }
  ],
  songs: [
    {
      id: "s1",
      title: "Azul Solar",
      artist: "Marina Norte",
      album: "Horizonte",
      durationSeconds: 214
    },
    {
      id: "s2",
      title: "Noite Curta",
      artist: "Os Vetores",
      album: "Cidade Acesa",
      durationSeconds: 188
    },
    {
      id: "s3",
      title: "Eco de Domingo",
      artist: "Lia Ramos",
      album: "Casa Aberta",
      durationSeconds: 241
    },
    {
      id: "s4",
      title: "Linha do Mar",
      artist: "Davi Prado",
      album: "Corrente",
      durationSeconds: 203
    },
    {
      id: "s5",
      title: "Baixo Contorno",
      artist: "Trio Aurora",
      album: "Depois das Seis",
      durationSeconds: 267
    }
  ],
  playlists: [
    {
      id: "p1",
      userId: "u1",
      name: "Manha leve",
      songIds: Array.from({ length: FEATURED_PLAYLIST_SONG_COUNT }, (_item, index) => `s${index + 1}`)
    },
    { id: "p2", userId: "u1", name: "Foco", songIds: ["s2", "s5"] },
    { id: "p3", userId: "u2", name: "Viagem", songIds: ["s1", "s2", "s4"] }
  ]
};

function generatedUsers() {
  const firstNames = [
    "Alice",
    "Bianca",
    "Caio",
    "Daniel",
    "Elisa",
    "Felipe",
    "Gabriela",
    "Heitor",
    "Isabela",
    "Jonas",
    "Laura",
    "Marcos",
    "Nina",
    "Otavio",
    "Paula",
    "Rafael",
    "Sofia",
    "Tiago",
    "Valeria",
    "Yuri"
  ];
  const surnames = [
    "Almeida",
    "Barbosa",
    "Campos",
    "Dias",
    "Freitas",
    "Gomes",
    "Lopes",
    "Martins",
    "Nogueira",
    "Pereira",
    "Rocha",
    "Santana"
  ];
  const users = [];
  for (let index = BASE_DATA.users.length + 1; index <= INITIAL_USER_COUNT; index += 1) {
    users.push({
      id: `u${index}`,
      name: `${firstNames[index % firstNames.length]} ${surnames[index % surnames.length]} ${String(index).padStart(3, "0")}`,
      email: `usuario${String(index).padStart(3, "0")}@example.com`
    });
  }
  return users;
}

function generatedSongs() {
  const titleWords = [
    "Aurora",
    "Cidade",
    "Circuito",
    "Delta",
    "Estrada",
    "Farol",
    "Jardim",
    "Litoral",
    "Neblina",
    "Pulso",
    "Ritmo",
    "Saturno",
    "Vento"
  ];
  const artists = [
    "Banda Central",
    "Duo Atlantico",
    "Grupo Prisma",
    "Lia e os Sinais",
    "Mar Aberto",
    "Norte Livre",
    "Projeto Beta",
    "Quarteto Solar",
    "Trio Estacao",
    "Vozes do Sul"
  ];
  const albums = ["Volume", "Sessao", "Arquivo", "Colecao", "Mapa", "Registro", "Caderno", "Ao Vivo"];
  const songs = [];
  for (let index = BASE_DATA.songs.length + 1; index <= INITIAL_SONG_COUNT; index += 1) {
    songs.push({
      id: `s${index}`,
      title: `${titleWords[index % titleWords.length]} ${String(index).padStart(3, "0")}`,
      artist: artists[index % artists.length],
      album: `${albums[index % albums.length]} ${String(1 + (index % 20)).padStart(2, "0")}`,
      durationSeconds: 120 + (index * 7) % 260
    });
  }
  return songs;
}

function generatedPlaylists() {
  const names = [
    "Trabalho",
    "Intervalo",
    "Treino",
    "Estrada",
    "Domingo",
    "Codigo",
    "Estudo",
    "Noite",
    "Cafe",
    "Viagem"
  ];
  const playlists = [];
  const featuredUserBaseCount = BASE_DATA.playlists.filter((playlist) => playlist.userId === "u1").length;
  const featuredSongBaseCount = BASE_DATA.playlists.filter((playlist) => playlist.songIds.includes("s1")).length;
  const featuredGeneratedCount = Math.min(
    Math.max(0, TARGET_USER_PLAYLIST_COUNT - featuredUserBaseCount),
    Math.max(0, TARGET_SONG_PLAYLIST_COUNT - featuredSongBaseCount),
    INITIAL_PLAYLIST_COUNT - BASE_DATA.playlists.length
  );
  const featuredGeneratedEnd = BASE_DATA.playlists.length + featuredGeneratedCount;
  for (let index = BASE_DATA.playlists.length + 1; index <= INITIAL_PLAYLIST_COUNT; index += 1) {
    let userId;
    let songIds;
    if (index <= featuredGeneratedEnd) {
      userId = "u1";
      songIds = ["s1"];
      let offset = 0;
      while (songIds.length < 5) {
        const songId = `s${1 + (((index * 7) + offset * 17) % INITIAL_SONG_COUNT)}`;
        if (!songIds.includes(songId)) {
          songIds.push(songId);
        }
        offset += 1;
      }
    } else {
      userId = `u${1 + ((index * 5) % INITIAL_USER_COUNT)}`;
      if (userId === "u1") {
        userId = "u2";
      }
      songIds = [];
      let offset = 0;
      while (songIds.length < 5) {
        const songId = `s${1 + (((index * 7) + offset * 17) % INITIAL_SONG_COUNT)}`;
        if (songId !== "s1" && !songIds.includes(songId)) {
          songIds.push(songId);
        }
        offset += 1;
      }
    }
    playlists.push({
      id: `p${index}`,
      userId,
      name: `${names[index % names.length]} ${String(index).padStart(3, "0")}`,
      songIds
    });
  }
  return playlists;
}

function buildInitialData() {
  return {
    users: [...BASE_DATA.users.map((user) => ({ ...user })), ...generatedUsers()],
    songs: [...BASE_DATA.songs.map((song) => ({ ...song })), ...generatedSongs()],
    playlists: [
      ...BASE_DATA.playlists.map((playlist) => ({ ...playlist, songIds: [...playlist.songIds] })),
      ...generatedPlaylists()
    ]
  };
}

const INITIAL_DATA = buildInitialData();

function clone(value) {
  if (Array.isArray(value)) {
    return value.map((item) => clone(item));
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, clone(item)])
    );
  }
  return value;
}

function requireString(value, fieldName) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new DomainError(400, "INVALID_INPUT", `${fieldName} e obrigatorio`);
  }
  return value.trim();
}

function optionalString(value, fieldName) {
  if (value === undefined || value === null) {
    return null;
  }
  return requireString(value, fieldName);
}

function requirePositiveNumber(value, fieldName) {
  const number = Number.parseInt(value, 10);
  if (!Number.isFinite(number) || number <= 0) {
    throw new DomainError(400, "INVALID_INPUT", `${fieldName} deve ser positivo`);
  }
  return number;
}

function normalizeSongIds(songIds) {
  if (songIds === undefined || songIds === null) {
    return [];
  }
  if (typeof songIds === "string") {
    return songIds
      .split(",")
      .map((songId) => songId.trim())
      .filter(Boolean);
  }
  if (!Array.isArray(songIds)) {
    throw new DomainError(400, "INVALID_INPUT", "songIds deve ser lista ou texto separado por virgulas");
  }
  return songIds.map((songId) => requireString(songId, "songId"));
}

function toMap(items) {
  return new Map(items.map((item) => [item.id, clone(item)]));
}

function listValues(items) {
  return [...items.values()].map((item) => clone(item));
}

function listFilteredValues(items, predicate) {
  return [...items.values()].filter(predicate).map((item) => clone(item));
}

function plainTypeName(itemType) {
  return itemType.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

export class MusicStore {
  constructor() {
    this.reset();
  }

  reset() {
    this.users = toMap(INITIAL_DATA.users);
    this.songs = toMap(INITIAL_DATA.songs);
    this.playlists = toMap(INITIAL_DATA.playlists);
    this.counters = {
      user: this.users.size + 1,
      song: this.songs.size + 1,
      playlist: this.playlists.size + 1
    };
    return { ok: true };
  }

  nextId(kind) {
    const prefixes = { user: "u", song: "s", playlist: "p" };
    const itemId = `${prefixes[kind]}${this.counters[kind]}`;
    this.counters[kind] += 1;
    return itemId;
  }

  assertExists(items, itemId, itemType) {
    if (!items.has(itemId)) {
      throw new DomainError(404, "NOT_FOUND", `${plainTypeName(itemType)} ${itemId} nao encontrado`);
    }
  }

  listUsers() {
    return listValues(this.users);
  }

  getUser(userId) {
    this.assertExists(this.users, userId, "Usuario");
    return clone(this.users.get(userId));
  }

  createUser(data = {}) {
    const user = {
      id: this.nextId("user"),
      name: requireString(data.name, "name"),
      email: requireString(data.email, "email")
    };
    this.users.set(user.id, user);
    return clone(user);
  }

  updateUser(userId, data = {}) {
    this.assertExists(this.users, userId, "Usuario");
    const current = this.users.get(userId);
    const updated = {
      ...current,
      name: optionalString(data.name, "name") || current.name,
      email: optionalString(data.email, "email") || current.email
    };
    this.users.set(userId, updated);
    return clone(updated);
  }

  deleteUser(userId) {
    this.assertExists(this.users, userId, "Usuario");
    this.users.delete(userId);
    this.playlists = new Map(
      [...this.playlists.entries()].filter(([, playlist]) => playlist.userId !== userId)
    );
    return { ok: true };
  }

  listSongs() {
    return listValues(this.songs);
  }

  getSong(songId) {
    this.assertExists(this.songs, songId, "Musica");
    return clone(this.songs.get(songId));
  }

  createSong(data = {}) {
    const song = {
      id: this.nextId("song"),
      title: requireString(data.title, "title"),
      artist: requireString(data.artist, "artist"),
      album: requireString(data.album, "album"),
      durationSeconds: requirePositiveNumber(data.durationSeconds, "durationSeconds")
    };
    this.songs.set(song.id, song);
    return clone(song);
  }

  updateSong(songId, data = {}) {
    this.assertExists(this.songs, songId, "Musica");
    const current = this.songs.get(songId);
    const updated = {
      ...current,
      title: optionalString(data.title, "title") || current.title,
      artist: optionalString(data.artist, "artist") || current.artist,
      album: optionalString(data.album, "album") || current.album,
      durationSeconds:
        data.durationSeconds === undefined || data.durationSeconds === null
          ? current.durationSeconds
          : requirePositiveNumber(data.durationSeconds, "durationSeconds")
    };
    this.songs.set(songId, updated);
    return clone(updated);
  }

  deleteSong(songId) {
    this.assertExists(this.songs, songId, "Musica");
    this.songs.delete(songId);
    for (const playlist of this.playlists.values()) {
      playlist.songIds = playlist.songIds.filter((currentId) => currentId !== songId);
    }
    return { ok: true };
  }

  listPlaylists(filters = {}) {
    const userId = filters.userId || null;
    const songId = filters.songId || null;

    if (userId) {
      this.assertExists(this.users, userId, "Usuario");
    }
    if (songId) {
      this.assertExists(this.songs, songId, "Musica");
    }

    return listFilteredValues(
      this.playlists,
      (playlist) =>
        (!userId || playlist.userId === userId) &&
        (!songId || playlist.songIds.includes(songId))
    );
  }

  getPlaylist(playlistId) {
    this.assertExists(this.playlists, playlistId, "Playlist");
    return clone(this.playlists.get(playlistId));
  }

  createPlaylist(data = {}) {
    const userId = requireString(data.userId, "userId");
    const songIds = normalizeSongIds(data.songIds);
    this.assertExists(this.users, userId, "Usuario");
    for (const songId of songIds) {
      this.assertExists(this.songs, songId, "Musica");
    }

    const playlist = {
      id: this.nextId("playlist"),
      userId,
      name: requireString(data.name, "name"),
      songIds
    };
    this.playlists.set(playlist.id, playlist);
    return clone(playlist);
  }

  updatePlaylist(playlistId, data = {}) {
    this.assertExists(this.playlists, playlistId, "Playlist");
    const current = this.playlists.get(playlistId);
    const userId = optionalString(data.userId, "userId") || current.userId;
    const songIds =
      data.songIds === undefined || data.songIds === null
        ? current.songIds
        : normalizeSongIds(data.songIds);

    this.assertExists(this.users, userId, "Usuario");
    for (const songId of songIds) {
      this.assertExists(this.songs, songId, "Musica");
    }

    const updated = {
      ...current,
      userId,
      name: optionalString(data.name, "name") || current.name,
      songIds
    };
    this.playlists.set(playlistId, updated);
    return clone(updated);
  }

  deletePlaylist(playlistId) {
    this.assertExists(this.playlists, playlistId, "Playlist");
    this.playlists.delete(playlistId);
    return { ok: true };
  }

  listUserPlaylists(userId) {
    this.assertExists(this.users, userId, "Usuario");
    return listFilteredValues(this.playlists, (playlist) => playlist.userId === userId);
  }

  listPlaylistSongs(playlistId) {
    this.assertExists(this.playlists, playlistId, "Playlist");
    return this.playlists
      .get(playlistId)
      .songIds.filter((songId) => this.songs.has(songId))
      .map((songId) => clone(this.songs.get(songId)));
  }

  listSongPlaylists(songId) {
    this.assertExists(this.songs, songId, "Musica");
    return listFilteredValues(this.playlists, (playlist) => playlist.songIds.includes(songId));
  }
}

export function plainError(error) {
  return {
    error: {
      code: error.code || "INTERNAL_ERROR",
      message: error.message || "Erro inesperado"
    }
  };
}
