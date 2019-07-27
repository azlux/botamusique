from rbRadios import RadioBrowser

rb = RadioBrowser()

def getstations_byname(query):
    results = rb.stations_byname(query)
    stations = []
    for st in results:
        try:
            # url = rb.playable_station(st['id'])['url']
            station = {'stationname': st['name'], 'id':st['id']}
            stations.append(station)
        except:
            pass
    return stations

def geturl_byid(id):
    url = rb.playable_station(id)['url']
    if url != None:
        return url
    else:
        return "-1"


if __name__ == "__main__":
    r = getstations_byname('r.sh')
    pass