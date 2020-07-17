# coding=utf-8
# Author: Dustyn Gibson <miigotu@gmail.com>
#
# URL: https://sickchill.github.io
#
# This file is part of SickChill.
#
# SickChill is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickChill is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickChill. If not, see <http://www.gnu.org/licenses/>.
# Stdlib Imports
import datetime
import time

# First Party Imports
import sickbeard
from sickbeard import logger, tvcache
from sickbeard.common import cpu_presets
from sickchill.helper.common import convert_size, try_int
from sickchill.providers.media.torrent import TorrentProvider


class RarbgProvider(TorrentProvider):

    def __init__(self):
        super().__init__('Rarbg', extra_options=('ranked', 'minseed', 'minleech', 'sorting', 'backlog', 'daily', 'enabled', 'custom_url'))

        self.__token = None
        self.__token_expires = None

        # Spec: https://torrentapi.org/apidocs_v2.txt
        self.url = "https://rarbg.to"
        self.urls = {"api": "http://torrentapi.org/pubapi_v2.php"}

        self.proper_strings = ["{{PROPER|REPACK}}"]

    def login(self):
        if self.__token and self.__token_expires and datetime.datetime.now() < self.__token_expires:
            return True

        login_params = {
            "get_token": "get_token",
            "format": "json",
            "app_id": "sickchill"
        }

        response = self.get_url(self.urls["api"], params=login_params, returns="json")
        if not response:
            logger.warning("Unable to connect to provider")
            return False

        self.__token = response.get("__token")
        self.__token_expires = datetime.datetime.now() + datetime.timedelta(minutes=14) if self.__token else None
        return self.__token is not None

    def search(self, search_strings, ep_obj=None) -> list:
        results = []
        if not self.login():
            return results

        search_params = {
            "app_id": "sickchill",
            "category": "tv",
            "min_seeders": self.config('minseed'),
            "min_leechers": self.config('minleech'),
            "limit": 100,
            "format": "json_extended",
            "ranked": try_int(self.config('ranked')),
            "__token": self.__token,
        }

        if ep_obj is not None:
            ep_indexerid = ep_obj.show.indexerid
            ep_indexer = ep_obj.idxr.slug
        else:
            ep_indexerid = None
            ep_indexer = None

        for mode in search_strings:
            items = []
            logger.debug("Search Mode: {0}".format(mode))
            if mode == "RSS":
                search_params["sort"] = "last"
                search_params["mode"] = "list"
                search_params.pop("search_string", None)
                search_params.pop("search_tvdb", None)
            else:
                search_params["sort"] = self.config('sorting')
                search_params["mode"] = "search"

                if ep_indexer == 'tvdb' and ep_indexerid:
                    search_params["search_tvdb"] = ep_indexerid
                else:
                    search_params.pop("search_tvdb", None)

            for search_string in search_strings[mode]:
                if mode != "RSS":
                    search_params["search_string"] = search_string
                    logger.debug("Search string: {0}".format(search_string))

                time.sleep(cpu_presets[sickbeard.CPU_PRESET])
                data = self.get_url(self.urls["api"], params=search_params, returns="json")
                if not isinstance(data, dict):
                    logger.debug("No data returned from provider")
                    continue

                error = data.get("error")
                error_code = data.get("error_code")
                # Don't log when {"error":"No results found","error_code":20}
                # List of errors: https://github.com/rarbg/torrentapi/issues/1#issuecomment-114763312
                if error:
                    if try_int(error_code) != 20:
                        logger.info(error)
                    continue

                torrent_results = data.get("torrent_results")
                if not torrent_results:
                    logger.debug("Data returned from provider does not contain any torrents")
                    continue

                for item in torrent_results:
                    try:
                        title = item.pop("title")
                        download_url = item.pop("download")
                        if not all([title, download_url]):
                            continue

                        seeders = item.pop("seeders")
                        leechers = item.pop("leechers")
                        if seeders < self.config('minseed') or leechers < self.config('minleech'):
                            if mode != "RSS":
                                logger.debug("Discarding torrent because it doesn't meet the"
                                           " minimum seeders or leechers: {0} (S:{1} L:{2})".format
                                           (title, seeders, leechers))
                            continue

                        torrent_size = item.pop("size", -1)
                        size = convert_size(torrent_size) or -1
                        torrent_hash = self.hash_from_magnet(download_url)

                        if mode != "RSS":
                            logger.debug("Found result: {0} with {1} seeders and {2} leechers".format
                                       (title, seeders, leechers))

                        result = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': torrent_hash}
                        items.append(result)
                    except Exception as e:
                        logger.info(e)

                    continue

            # For each search mode sort all the items by seeders
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items

        return results


