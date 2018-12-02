import requests
from datetime import datetime, timezone
from influxdb import InfluxDBClient

from Varken.logger import logging
from Varken.helpers import Movie, Queue


class RadarrAPI(object):
    def __init__(self, servers, influx_server):
        self.now = datetime.now(timezone.utc).astimezone().isoformat()
        self.influx = InfluxDBClient(influx_server.url, influx_server.port, influx_server.username,
                                     influx_server.password, 'plex2')
        self.servers = servers
        # Create session to reduce server web thread load, and globally define pageSize for all requests
        self.session = requests.Session()

    def influx_push(self, payload):
        # TODO: error handling for failed connection
        self.influx.write_points(payload)

    @logging
    def get_missing(self, notimplemented):
        endpoint = '/api/movie'
        self.now = datetime.now(timezone.utc).astimezone().isoformat()
        influx_payload = []

        for server in self.servers:
            missing = []
            headers = {'X-Api-Key': server.api_key}
            get = self.session.get(server.url + endpoint, headers=headers, verify=server.verify_ssl).json()
            movies = [Movie(**movie) for movie in get]

            for movie in movies:
                if server.get_missing:
                    if not movie.downloaded and movie.isAvailable:
                        ma = True
                    else:
                        ma = False
                    movie_name = '{} ({})'.format(movie.title, movie.year)
                    missing.append((movie_name, ma, movie.tmdbId))

            for title, ma, mid in missing:
                influx_payload.append(
                    {
                        "measurement": "Radarr",
                        "tags": {
                            "Missing": True,
                            "Missing_Available": ma,
                            "tmdbId": mid,
                            "server": server.id
                        },
                        "time": self.now,
                        "fields": {
                            "name": title
                        }
                    }
                )

        self.influx_push(influx_payload)

    @logging
    def get_queue(self, notimplemented):
        endpoint = '/api/queue'
        self.now = datetime.now(timezone.utc).astimezone().isoformat()
        influx_payload = []

        for server in self.servers:
            queue = []
            headers = {'X-Api-Key': server.api_key}
            get = self.session.get(server.url + endpoint, headers=headers, verify=server.verify_ssl).json()
            for movie in get:
                movie['movie'] = Movie(**movie['movie'])
            download_queue = [Queue(**movie) for movie in get]

            for queue_item in download_queue:
                name = '{} ({})'.format(queue_item.movie.title, queue_item.movie.year)

                if queue_item.protocol.upper() == 'USENET':
                    protocol_id = 1
                else:
                    protocol_id = 0

                queue.append((name, queue_item.quality['quality']['name'], queue_item.protocol.upper(),
                              protocol_id, queue_item.id))

            for movie, quality, protocol, protocol_id, qid in queue:
                influx_payload.append(
                    {
                        "measurement": "Radarr",
                        "tags": {
                            "type": "Queue",
                            "tmdbId": qid,
                            "server": server.id
                        },
                        "time": self.now,
                        "fields": {
                            "name": movie,
                            "quality": quality,
                            "protocol": protocol,
                            "protocol_id": protocol_id
                        }
                    }
                )

        self.influx_push(influx_payload)
