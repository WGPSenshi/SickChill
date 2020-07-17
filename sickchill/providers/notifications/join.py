# coding=utf-8
# Author: Author: Gonçalo M. (aka duramato/supergonkas) <supergonkas@gmail.com>
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
import urllib

# First Party Imports
import sickbeard
from sickbeard import logger
from sickbeard.common import (NOTIFY_DOWNLOAD, NOTIFY_GIT_UPDATE, NOTIFY_GIT_UPDATE_TEXT, NOTIFY_LOGIN, NOTIFY_LOGIN_TEXT, NOTIFY_SNATCH,
                              NOTIFY_SUBTITLE_DOWNLOAD, notifyStrings)

# Local Folder Imports
from .base import AbstractNotifier


class Notifier(AbstractNotifier):
    """
    Use Join to send notifications

    http://joaoapps.com/join/
    """
    def test_notify(self, id=None, apikey=None):
        """
        Send a test notification
        :param id: The Device ID
        :param id: The User's API Key
        :returns: the notification
        """
        return self._notify_join('Test', 'This is a test notification from SickChill', id, apikey, force=True)

    def _send_join_msg(self, title, msg, id=None, apikey=None):
        """
        Sends a Join notification

        :param title: The title of the notification to send
        :param msg: The message string to send
        :param id: The Device ID
        :param id: The User's API Key

        :returns: True if the message succeeded, False otherwise
        """
        id = sickbeard.JOIN_ID if id is None else id
        apikey = sickbeard.JOIN_APIKEY if apikey is None else apikey

        logger.debug('Join in use with device ID: {0}'.format(id))

        message = '{0} : {1}'.format(title.encode(), msg.encode())
        params = {
            "apikey": apikey,
            "deviceId": id,
            "title": title,
            "text": message,
            "icon": "https://raw.githubusercontent.com/SickChill/SickChill/master/gui/slick/images/sickchill.png"
        }
        payload = urllib.parse.urlencode(params)
        join_api = 'https://joinjoaomgcd.appspot.com/_ah/api/messaging/v1/sendPush?' + payload
        logger.debug('Join url in use : {0}'.format(join_api))
        success = False
        try:
            urllib.request.urlopen(join_api)
            message = 'Join message sent successfully.'
            logger.debug('Join message returned : {0}'.format(message))
            success = True
        except Exception as e:
            message = 'Error while sending Join message: {0} '.format(e)
        finally:
            logger.info(message)
            return success, message

    def notify_snatch(self, name, title=notifyStrings[NOTIFY_SNATCH]):
        """
        Sends a Join notification when an episode is snatched

        :param name: The name of the episode snatched
        :param title: The title of the notification to send
        """
        if self.config('snatch'):
            self._notify_join(title, name)

    def notify_download(self, name, title=notifyStrings[NOTIFY_DOWNLOAD]):
        """
        Sends a Join notification when an episode is downloaded

        :param name: The name of the episode downloaded
        :param title: The title of the notification to send
        """
        if self.config('download'):
            self._notify_join(title, name)

    def notify_subtitle_download(self, name, lang, title=notifyStrings[NOTIFY_SUBTITLE_DOWNLOAD]):
        """
        Sends a Join notification when subtitles for an episode are downloaded

        :param name: The name of the episode subtitles were downloaded for
        :param lang: The language of the downloaded subtitles
        :param title: The title of the notification to send
        """
        if self.config('subtitle'):
            self._notify_join(title, '{0}: {1}'.format(name, lang))

    def notify_git_update(self, new_version='??'):
        """
        Sends a Join notification for git updates

        :param new_version: The new version available from git
        """
        if self.config('enabled'):
            update_text = notifyStrings[NOTIFY_GIT_UPDATE_TEXT]
            title = notifyStrings[NOTIFY_GIT_UPDATE]
            self._notify_join(title, update_text + new_version)

    def notify_login(self, ipaddress=''):
        """
        Sends a Join notification on login

        :param ipaddress: The IP address the login is originating from
        """
        if self.config('enabled'):
            update_text = notifyStrings[NOTIFY_LOGIN_TEXT]
            title = notifyStrings[NOTIFY_LOGIN]
            self._notify_join(title, update_text.format(ipaddress))

    def _notify_join(self, title, message, id=None, apikey=None, force=False):
        """
        Sends a Join notification

        :param title: The title of the notification to send
        :param message: The message string to send
        :param id: The Device ID
        :param id: The User's API Key
        :param force: Enforce sending, for instance for testing

        :returns: the message to send
        """

        if not (force or self.config('enabled')):
            logger.debug('Notification for Join not enabled, skipping this notification')
            return False, 'Disabled'

        logger.debug('Sending a Join message for {0}'.format(message))

        return self._send_join_msg(title, message, id, apikey)