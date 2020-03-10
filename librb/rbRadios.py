import requests

from xml.etree import ElementTree
from urllib.parse import urljoin

from librb.rbConstants import endpoints, BASE_URL


def request(endpoint, **kwargs):

    fmt = kwargs.get("format", "json")

    if fmt == "xml":
        content_type = "application/%s" % fmt
    else:
        content_type = "application/%s" % fmt

    headers = {"content-type": content_type, "User-Agent": "pyradios/dev"}

    params = kwargs.get("params", {})

    url = BASE_URL + endpoint

    resp = requests.get(url, headers=headers, params=params)

    if resp.status_code == 200:
        if fmt == "xml":
            return resp.text
        return resp.json()

    return resp.raise_for_status()


class EndPointBuilder:
    def __init__(self, fmt="json"):
        self.fmt = fmt
        self._option = None
        self._endpoint = None

    @property
    def endpoint(self):
        return endpoints[self._endpoint][self._option]

    def produce_endpoint(self, **parts):
        self._option = len(parts)
        self._endpoint = parts["endpoint"]
        parts.update({"fmt": self.fmt})
        return self.endpoint.format(**parts)


class RadioBrowser:
    def __init__(self, fmt="json"):
        self.fmt = fmt
        self.builder = EndPointBuilder(fmt=self.fmt)

    def countries(self, filter=""):
        endpoint = self.builder.produce_endpoint(endpoint="countries")
        return request(endpoint)

    def codecs(self, filter=""):
        endpoint = self.builder.produce_endpoint(endpoint="codecs")
        return request(endpoint)

    def states(self, country="", filter=""):
        endpoint = self.builder.produce_endpoint(
            endpoint="states", country=country, filter=filter
        )
        return request(endpoint)

    def languages(self, filter=""):
        endpoint = self.builder.produce_endpoint(endpoint="languages", filter=filter)
        return request(endpoint)

    def tags(self, filter=""):
        endpoint = self.builder.produce_endpoint(endpoint="tags", filter=filter)
        return request(endpoint)

    def stations(self, **params):
        endpoint = self.builder.produce_endpoint(endpoint="stations")
        kwargs = {}
        if params:
            kwargs.update({"params": params})
        return request(endpoint, **kwargs)

    def stations_byid(self, id):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="byid", search_term=id
        )
        return request(endpoint)

    def stations_byuuid(self, uuid):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="byuuid", search_term=uuid
        )
        return request(endpoint)

    def stations_byname(self, name):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="byname", search_term=name
        )
        return request(endpoint)

    def stations_bynameexact(self, nameexact):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="bynameexact", search_term=nameexact
        )
        return request(endpoint)

    def stations_bycodec(self, codec):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="bycodec", search_term=codec
        )
        return request(endpoint)

    def stations_bycodecexact(self, codecexact):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="bycodecexact", search_term=codecexact
        )
        return request(endpoint)

    def stations_bycountry(self, country):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="bycountry", search_term=country
        )
        return request(endpoint)

    def stations_bycountryexact(self, countryexact):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="bycountryexact", search_term=countryexact
        )
        return request(endpoint)

    def stations_bystate(self, state):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="bystate", search_term=state
        )
        return request(endpoint)

    def stations_bystateexact(self, stateexact):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="bystateexact", search_term=stateexact
        )
        return request(endpoint)

    #
    def stations_bylanguage(self, language):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="bylanguage", search_term=language
        )
        return request(endpoint)

    def stations_bylanguageexact(self, languageexact):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="bylanguageexact", search_term=languageexact
        )
        return request(endpoint)

    def stations_bytag(self, tag):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="bytag", search_term=tag
        )
        return request(endpoint)

    def stations_bytagexact(self, tagexact):
        endpoint = self.builder.produce_endpoint(
            endpoint="stations", by="bytagexact", search_term=tagexact
        )
        return request(endpoint)

    def playable_station(self, station_id):
        endpoint = self.builder.produce_endpoint(
            endpoint="playable_station", station_id=station_id, ver="v2"
        )

        return request(endpoint)

    def station_search(self, params, **kwargs):
        # http://www.radio-browser.info/webservice#Advanced_station_search
        assert isinstance(params, dict), "params is not a dict"
        kwargs["params"] = params
        endpoint = self.builder.produce_endpoint(endpoint="station_search")
        return request(endpoint, **kwargs)
