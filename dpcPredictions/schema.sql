DROP TABLE IF EXISTS player;
DROP TABLE IF EXISTS team;
DROP TABLE IF EXISTS user;

CREATE TABLE player (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nickname TEXT NOT NULL,
  firstname TEXT NOT NULL,
  lastname TEXT NOT NULL,
  position TEXT,
  team TEXT NOT NULL,
  FOREIGN KEY (team) REFERENCES team (name)
);

CREATE TABLE team (
  name TEXT PRIMARY KEY NOT NULL,
  points INTEGER NOT NULL,
  region TEXT,
  earnings INTEGER
);

CREATE TABLE tournament (
  name TEXT PRIMARY KEY NOT NULL,
  type TEXT,
  prize_pool INTEGER,
  organizer TEXT,

);

CREATE TABLE match (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  dota_match_id TEXT,
  FOREIGN KEY team_a TEXT team,
  FOREIGN KEY team_b TEXT team,
  score_team_a INT NOT NULL,
  score_team_b INT NOT NULL
  FOREIGN KEY ()
);

CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL
);