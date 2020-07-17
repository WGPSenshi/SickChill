# coding=utf-8
# Author: Dustyn Gibson <miigotu@gmail.com>
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
# Third Party Imports
import validators
from requests.compat import urljoin

# First Party Imports
from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser
from sickchill.helper.common import try_int
from sickchill.providers.media.torrent import TorrentProvider


class SkyTorrents(TorrentProvider):

    def __init__(self):

        super().__init__('SkyTorrents', extra_options=tuple([]))

        self.url = "https://www.skytorrents.lol"
        # https://www.skytorrents.lol/?query=arrow&category=show&tag=hd&sort=seeders&type=video
        # https://www.skytorrents.lol/top100?category=show&type=video&sort=created
        self.urls = {"search": urljoin(self.url, "/"), 'rss': urljoin(self.url, "/top100")}

    def search(self, search_strings, ep_obj=None) -> list:
        results = []
        for mode in search_strings:
            items = []
            logger.debug("Search Mode: {0}".format(mode))
            for search_string in search_strings[mode]:
                if mode != "RSS":
                    logger.debug("Search string: {0}".format(search_string))

                search_url = (self.urls["search"], self.urls["rss"])[mode == "RSS"]
                if self.config('custom_url'):
                    if not validators.url(self.config('custom_url')):
                        logger.warning("Invalid custom url: {0}".format(self.config('custom_url')))
                        return results
                    search_url = urljoin(self.config('custom_url'), search_url.split(self.url)[1])

                if mode != "RSS":
                    search_params = {'query': search_string, 'sort': ('seeders', 'created')[mode == 'RSS'], 'type': 'video', 'tag': 'hd', 'category': 'show'}
                else:
                    search_params = {'category': 'show', 'type': 'video', 'sort': 'created'}

                data = self.get_url(search_url, params=search_params, returns='text')
                if not data:
                    logger.debug('Data returned from provider does not contain any torrents')
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    labels = [label.get_text(strip=True) for label in html('th')]
                    for item in html('tr', attrs={'data-size': True}):
                        try:
                            size = try_int(item['data-size'])
                            cells = item.findChildren('td')

                            title_block_links = cells[labels.index('Name')].find_all('a')
                            title = title_block_links[0].get_text(strip=True)
                            info_hash = title_block_links[0]['href'].split('/')[1]
                            download_url = title_block_links[2]['href']

                            seeders = try_int(cells[labels.index('Seeders')].get_text(strip=True))
                            leechers = try_int(cells[labels.index('Leechers')].get_text(strip=True))

                            if seeders < self.config('minseed') or leechers < self.config('minleech'):
                                if mode != "RSS":
                                    logger.debug("Discarding torrent because it doesn't meet the minimum seeders or leechers: {0} (S:{1} L:{2})".format
                                               (title, seeders, leechers))
                                continue

                            item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': info_hash}
                            if mode != "RSS":
                                logger.debug("Found result: {0} with {1} seeders and {2} leechers".format(title, seeders, leechers))

                            items.append(item)

                        except (AttributeError, TypeError, KeyError, ValueError):
                            continue

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)

            results += items

        return results

