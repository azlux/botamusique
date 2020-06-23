#!/usr/bin/env bash

case "$1" in
    stable)
        curl -Lo /tmp/botamusique.tar.gz https://packages.azlux.fr/botamusique/sources.tar.gz
        tar -xzf /tmp/botamusique.tar.gz -C /tmp/
        cp -r /tmp/botamusique/* .
        rm -r /tmp/botamusique
        rm -r /tmp/botamusique.tar.gz
        ;;
    testing)
        curl -Lo /tmp/botamusique.tar.gz https://packages.azlux.fr/botamusique/sources-testing.tar.gz
        tar -xzf /tmp/botamusique.tar.gz -C /tmp/
        cp -r /tmp/botamusique/* .
        rm -r /tmp/botamusique
        rm -r /tmp/botamusique.tar.gz
        ;;
    *)
        ;;
esac
exit 0
