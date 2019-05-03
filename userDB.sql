DROP DATABASE IF EXISTS Government

CREATE DATABASE Government
USE Government

DROP TABLE IF EXISTS users

CREATE TABLE users (
  user_id         BIGINT          UNSIGNED NOT NULL
  username        VARCHAR(144)
  experience      INT(10)         DEFAULT 0
  trivia_correct  SMALLINT        DEFAULT 0
  trivia_attempt  SMALLINT        DEFAULT 0
  hard_r          SMALLINT        DEFAULT 0
  soft_a          SMALLINT        DEFAULT 0
  PRIMARY KEY (user_id)
) ENGINE=InnoDB

CREATE TABLE guilds (
  guild_id        BIGINT          UNSIGNED NOT NULL,
  user_id         BIGINT          UNSIGNED NOT NULL,
  guildexp        INT(10)         DEFAULT 0
) ENGINE=InnoDB
