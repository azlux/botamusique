curl -Lo /tmp/botamusique.tar.gz https://azlux.fr/botamusique/sources.tar.gz
tar -xzf /tmp/botamusique.tar.gz -C /tmp/
cp -r /tmp/botamusique/* .
rm -r /tmp/botamusique
rm -r /tmp/botamusique.tar.gz
