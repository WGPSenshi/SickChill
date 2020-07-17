# coding=utf-8
# Author: medariox <dariox@gmx.com>
# based on Dustyn Gibson's <miigotu@gmail.com> work
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
import re

# Third Party Imports
from requests.utils import dict_from_cookiejar

# First Party Imports
from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser
from sickchill.helper.common import convert_size, try_int
from sickchill.helper.exceptions import AuthException
from sickchill.providers.media.torrent import TorrentProvider


class GFTrackerProvider(TorrentProvider):

    def __init__(self):

        # Provider Init
        super().__init__('GFTracker', extra_options=('username', 'password', 'minseed', 'minleech'))

        # URLs
        self.url = 'https://www.thegft.org/'
        self.urls = {
            'login': self.url + 'loginsite.php',
            'search': self.url + 'browse.php',
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL']

    def _check_auth(self):

        if not self.config('username') or not self.config('password'):
            raise AuthException("Your authentication credentials for " + self.name + " are missing, check your config.")

        return True

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.config('username'),
            'password': self.config('password'),
        }

        # Initialize session with a GET to have cookies
        self.get_url(self.url, returns='text')
        response = self.get_url(self.urls['login'], post_data=login_params, returns='text')
        if not response:
            logger.warning("Unable to connect to provider")
            return False

        if re.search('Username or password incorrect', response):
            logger.warning("Invalid username or password. Check your settings")
            return False

        return True

    def search(self, search_strings, ep_obj=None) -> list:
        results = []
        if not self.login():
            return results

        # https://www.thegft.org/browse.php?view=0&c26=1&c37=1&c19=1&c47=1&c17=1&c4=1&search=arrow
        # Search Params
        search_params = {
            'view': 0,  # BROWSE
            'c4': 1,  # TV/XVID
            'c17': 1,  # TV/X264
            'c19': 1,  # TV/DVDRIP
            'c26': 1,  # TV/BLURAY
            'c37': 1,  # TV/DVDR
            'c47': 1,  # TV/SD
            'search': '',
        }

        # Units
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

        def process_column_header(td):
            result = ''
            if td.a and td.a.img:
                result = td.a.img.get('title', td.a.get_text(strip=True))
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

                search_params['search'] = search_string

                data = self.get_url(self.urls['search'], params=search_params, returns='text')
                if not data:
                    logger.debug("No data returned from provider")
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_table = html.find('div', id='torrentBrowse')
                    torrent_rows = torrent_table('tr') if torrent_table else []

                    # Continue only if at least one Release is found
                    if len(torrent_rows) < 2:
                        logger.debug("Data returned from provider does not contain any torrents")
                        continue

                    labels = [process_column_header(label) for label in torrent_rows[0]('td')]

                    # Skip column headers
                    for result in torrent_rows[1:]:

                        try:
                            cells = result('td')

                            title = cells[labels.index('Name')].find('a').find_next('a')['title'] or cells[labels.index('Name')].find('a')['title']
                            download_url = self.url + cells[labels.index('DL')].find('a')['href']
                            if not all([title, download_url]):
                                continue

                            peers = cells[labels.index('S/L')].get_text(strip=True).split('/', 1)
                            seeders = try_int(peers[0])
                            leechers = try_int(peers[1])

                            # Filter unseeded torrent
                            if seeders < self.config('minseed') or leechers < self.config('minleech'):
                                if mode != 'RSS':
                                    logger.debug("Discarding torrent because it doesn't meet the"
                                               " minimum seeders or leechers: {0} (S:{1} L:{2})".format
                                               (title, seeders, leechers))
                                continue

                            torrent_size = cells[labels.index('Size/Snatched')].get_text(strip=True).split('/', 1)[0]
                            size = convert_size(torrent_size, units=units) or -1

                            item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': ''}
                            if mode != 'RSS':
                                logger.debug("Found result: {0} with {1} seeders and {2} leechers".format
                                           (title, seeders, leechers))

                            items.append(item)
                        except Exception:
                            continue

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items

        return results


