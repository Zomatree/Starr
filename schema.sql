create user starr with createdb password 'starr';
create database starr owner = 'starr';

\c starr;

create table server_configs (
    prefix text,
    star_count int not null default 3,
    starboard_channel text,
    server_id text primary key
);

create table stars (
    user_id text not null,
    server_id text not null references server_configs(server_id),
    channel_id text not null,
    message_id text not null,

    unique (user_id, message_id)
);

create table starred_messages (
    starboard_channel_message text not null,
    original_message text not null
);
