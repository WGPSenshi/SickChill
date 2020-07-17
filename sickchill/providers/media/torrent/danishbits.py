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
import json

# First Party Imports
from sickbeard import logger, tvcache
from sickchill.helper.common import convert_size, try_int
from sickchill.providers.media.torrent import TorrentProvider


class DanishbitsProvider(TorrentProvider):

    def __init__(self):

        # Provider Init
        super().__init__('Danishbits', extra_options=('username', 'password', 'minseed', 'minleech', 'freeleech'))

        # URLs
        self.url = 'https://danishbits.org/'
        self.urls = {
            'login': self.url + 'login.php',
            'search': self.url + 'couchpotato.php',
        }

    def search(self, search_strings, ep_obj=None) -> list:
        results = []
        if not self.login():
            return results

        # Search Params
        search_params = {
            'user': self.config('username'),
            'passkey': self.config('password'),
            'search': '.',  # Dummy query for RSS search, needs the search param sent.
            'latest': 'true'
        }

        # Units
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

        def process_column_header(td):
            result = ''
            if td.img:
                result = td.img.get('title')
            if not result:
                result = td.get_text(strip=True)
            return result

        for mode in search_strings:
            items = []
            logger.debug("Search Mode: {0}".format(mode))

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.debug("Search string: {0}".format
                               (search_string))

                    search_params['latest'] = 'false'
                    search_params['search'] = search_string

                data = self.get_url(self.urls['search'], params=search_params, returns='text')
                if not data:
                    logger.debug("No data returned from provider")
                    continue

                result = json.loads(data)
                if 'results' in result:
                    for torrent in result['results']:
                        title = torrent['release_name']
                        download_url = torrent['download_url']
                        seeders  = torrent['seeders']
                        leechers  = torrent['leechers']
                        if seeders < self.config('minseed') or leechers < self.config('minleech'):
                            logger.info("Discarded {0} because with {1}/{2} seeders/leechers does not meet the requirement of {3}/{4} seeders/leechers".format(title, seeders, leechers, self.config('minseed'), self.config('minleech')))
                            continue

                        if self.config('freeleech') and not torrent['freeleech']:
                            continue

                        size = convert_size(torrent['size'], units=units) or -1
                        item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders,
                                'leechers': leechers, 'hash': ''}
                        logger.debug("Found result: {0} with {1} seeders and {2} leechers".format
                                                    (title, seeders, leechers))
                        items.append(item)

                if 'error' in result:
                    logger.warning(result['error'])

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items

        return results


