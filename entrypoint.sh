#!/usr/bin/env bash
command=( "${@}" )

if [ -n "$BAM_DB" ]; then
    command+=( "--db" "$BAM_DB" )
fi

if [ -n "$BAM_MUSIC_DB" ]; then
    command+=( "--music-db" "$BAM_MUSIC_DB" )
fi

if [ -n "$BAM_MUMBLE_SERVER" ]; then
    command+=( "--server" "$BAM_MUMBLE_SERVER")
fi

if [ -n "$BAM_MUMBLE_PASSWORD" ]; then
    command+=( "--password" "$BAM_MUMBLE_PASSWORD" )
fi

if [ -n "$BAM_MUMBLE_PORT" ]; then
    command+=( "--port" "$BAM_MUMBLE_PORT" )
fi

if [ -n "$BAM_USER" ]; then
    command+=( "--user" "$BAM_USER" )
fi

if [ -n "$BAM_TOKENS" ]; then
    command+=( "--tokens" "$BAM_TOKENS" )
fi

if [ -n "$BAM_CHANNEL" ]; then
    command+=( "--channel" "$BAM_CHANNEL" )
fi

if [ -n "$BAM_CERTIFICATE" ]; then
    command+=( "--cert" "$BAM_CERTIFICATE" )
fi

if [ -n "$BAM_VERBOSE" ]; then
    command+=( "--verbose" )
fi

if [ -n "$BAM_CONFIG_file" ]; then
    if [ ! -f "$BAM_CONFIG_file" ]; then
        cp "/botamusique/configuration.example.ini" "$BAM_CONFIG_file"
    fi
    command+=( "--config" "$BAM_CONFIG_file" )
else
    if [ ! -f "/botamusique/configuration.ini" ]; then
        cp "/botamusique/configuration.example.ini" "/botamusique/configuration.ini"
    fi
    command+=( "--config" "/botamusique/configuration.ini" )
fi

exec "${command[@]}"
