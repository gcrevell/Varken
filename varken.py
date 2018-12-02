import schedule
import threading
from time import sleep

from Varken.iniparser import INIParser
from Varken.sonarr import SonarrAPI
from Varken.tautulli import TautulliAPI
from Varken.radarr import RadarrAPI


def threaded(job, days=None):
    thread = threading.Thread(target=job, args=([days]))
    thread.start()


if __name__ == "__main__":
    CONFIG = INIParser()

    if CONFIG.sonarr_enabled:
        SONARR = SonarrAPI(CONFIG.sonarr_servers, CONFIG.influx_server)

        for server in CONFIG.sonarr_servers:
            if server.queue:
                schedule.every(server.queue_run_seconds).seconds.do(threaded, SONARR.get_queue)
            if server.missing_days > 0:
                schedule.every(server.missing_days_run_seconds).seconds.do(threaded, SONARR.get_missing,
                                                                           server.missing_days)
            if server.future_days > 0:
                schedule.every(server.future_days_run_seconds).seconds.do(threaded, SONARR.get_future,
                                                                          server.future_days)

    if CONFIG.tautulli_enabled:
        TAUTULLI = TautulliAPI(CONFIG.tautulli_servers, CONFIG.influx_server)

        for server in CONFIG.tautulli_servers:
            if server.get_activity:
                schedule.every(server.get_activity_run_seconds).seconds.do(threaded, TAUTULLI.get_activity)
            if server.get_sessions:
                schedule.every(server.get_sessions_run_seconds).seconds.do(threaded, TAUTULLI.get_sessions)

    if CONFIG.radarr_enabled:
        RADARR = RadarrAPI(CONFIG.radarr_servers, CONFIG.influx_server)

        for server in CONFIG.radarr_servers:
            if any([server.get_missing, server.get_missing_available]):
                schedule.every(server.get_missing_run_seconds).seconds.do(threaded, RADARR.get_missing)
            if server.queue:
                schedule.every(server.queue_run_seconds).seconds.do(threaded, RADARR.get_queue)



    while True:
        schedule.run_pending()
        sleep(1)

