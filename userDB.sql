DROP DATABASE IF EXISTS Government

CREATE DATABASE Government
USE Government

-- intended structures for DB:

-- per user: stat tracking only.
-- per guild: server preferences, active channels
-- global: not necessary (maybe tracking shards or something)

-- users collated into a single table.
-- we can track user logs from here.

DROP TABLE IF EXISTS users

CREATE TABLE users (
  -- userID passed from discord api -- unsigned is best way to fit the #
  user_id         BIGINT          UNSIGNED NOT NULL
  -- funky user names will break everything
  username        VARCHAR(144)    NOT NULL CHARACTER SET utf32 COLLATE utf32_general_ci
  -- user tracking
  experience      INT(10)         DEFAULT 0
  -- trivia tracking
  trivia_correct  SMALLINT        DEFAULT 0
  trivia_attempt  SMALLINT        DEFAULT 0
  -- vip
  hard_r          SMALLINT        DEFAULT 0
  soft_a          SMALLINT        DEFAULT 0
  PRIMARY KEY (user_id)
) ENGINE=InnoDB
