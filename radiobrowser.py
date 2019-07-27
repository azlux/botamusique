from radios import RadioBrowser

rb = RadioBrowser()

def getstations_byname(query):
    results = rb.stations_byname(query)
    stations = []
    for st in results:
        try:
            url = rb.playable_station(st['id'])['url']
            station = {'stationname': st['name'], 'url': url, 'id':st['id']}
            stations.append(station)
        except:
            pass
    return stations


if __name__ == "__main__":
    r = getstations_byname('r.sh')
    pass