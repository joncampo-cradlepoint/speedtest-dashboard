"""
NCOS communication module for SDK applications.

Copyright (c) 2018 Cradlepoint, Inc. <www.cradlepoint.com>.  All rights reserved.

This file contains confidential information of CradlePoint, Inc. and your use of
this file is subject to the CradlePoint Software License Agreement distributed with
this file. Unauthorized reproduction or distribution of this file is subject to civil and
criminal penalties.
"""

import json
import re
import socket
import sys


class SdkCSException(Exception):
    pass


CSCLIENT_NAME = 'SDK CSClient'


class CSClient(object):
    """
    The CSClient class is the NCOS SDK mechanism for communication between apps and the router tree/config store.
    Instances of this class communicate with the router using either an explicit socket or with http method calls.

    Apps running locally on the router use a socket on the router to send commands from the app to the router tree
    and to receive data (JSON) from the router tree.
    """
    END_OF_HEADER = b"\r\n\r\n"
    STATUS_HEADER_RE = re.compile(b"status: \w*")
    CONTENT_LENGTH_HEADER_RE = re.compile(b"content-length: \w*")
    MAX_PACKET_SIZE = 8192
    RECV_TIMEOUT = 2.0

    _instances = {}

    @classmethod
    def is_initialized(cls):
        return cls in cls._instances

    def __new__(cls, *na, **kwna):
        """ Singleton factory (with subclassing support) """
        if not cls.is_initialized():
            cls._instances[cls] = super().__new__(cls)
        return cls._instances[cls]

    def __init__(self, init=False):
        if not init:
            return

    def get(self, base, query='', tree=0):
        """
        Constructs and sends a get request to retrieve specified data from a device.

        The behavior of this method is contextual:
            - If the app is installed on (and executed from) a device, it directly queries the router tree to retrieve the
              specified data.
            - If the app running remotely from a computer it calls the HTTP GET method to retrieve the specified data.

        Args:
            base: String representing a path to a resource on a router tree,
                  (i.e. '/config/system/logging/level').
            query: Not required.
            tree: Not required.

        Returns:
            A dictionary containing the response (i.e. {"success": True, "data:": {}}

        """
        cmd = "get\n{}\n{}\n{}\n".format(base, query, tree)
        return self._dispatch(cmd)

    def put(self, base, value='', query='', tree=0):
        """
        Constructs and sends a put request to update or add specified data to the device router tree.

        The behavior of this method is contextual:
            - If the app is installed on(and executed from) a device, it directly updates or adds the specified data to
              the router tree.
            - If the app running remotely from a computer it calls the HTTP PUT method to update or add the specified
              data.

        Args:
            base: String representing a path to a resource on a router tree,
                  (i.e. '/config/system/logging/level').
            value: Not required.
            query: Not required.
            tree: Not required.

        Returns:
            A dictionary containing the response (i.e. {"success": True, "data:": {}}
        """
        value = json.dumps(value).replace(' ', '')
        cmd = "put\n{}\n{}\n{}\n{}\n".format(base, query, tree, value)
        return self._dispatch(cmd)

    def alert(self, app_name='', value=''):
        """
        Constructs and sends a custom alert to NCM for the device. Apps calling this method must be running
        on the target device to send the alert. If invoked while running on a computer, then only a log is output.

        Args:
        app_name: String name of your application.
        value: String to displayed for the alert.

        Returns:
            Success: None
            Failure: An error
        """
        cmd = "alert\n{}\n{}\n".format(app_name, value)
        return self._dispatch(cmd)

    def log(self, name='', value=''):
        """
        Adds a DEBUG log to the device SYSLOG.
        Note: It is recommend that app_logging.py be used for logging which
              supports all logging levels.

        Args:
        name: String of the name of your application.
        value: String text for the log.

        Returns:
        None
        """
        cmd = "log\n{}\n{}\n".format(name, value)
        return self._dispatch(cmd)

    def _safe_dispatch(self, cmd):
        """Send the command and return the response."""
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect('/var/tmp/cs.sock')
            sock.sendall(bytes(cmd, 'ascii'))
            return self._receive(sock)

    def _dispatch(self, cmd):
        errmsg = None
        result = ""
        try:
            result = self._safe_dispatch(cmd)
        except Exception as err:
            # ignore the command error, continue on to next command
            errmsg = "dispatch failed with exception={} err={}".format(type(err), str(err))
        if errmsg is not None:
            self.log(CSCLIENT_NAME, errmsg)
            pass
        return result

    def _safe_receive(self, sock):
        sock.settimeout(self.RECV_TIMEOUT)
        data = b""
        eoh = -1
        while eoh < 0:
            # In the event that the config store times out in returning data, lib returns
            # an empty result. Then again, if the config store hangs for 2+ seconds,
            # the app's behavior is the least of our worries.
            try:
                buf = sock.recv(self.MAX_PACKET_SIZE)
            except socket.timeout:
                return {"status": "timeout", "data": None}
            if len(buf) == 0:
                break
            data += buf
            eoh = data.find(self.END_OF_HEADER)

        status_hdr = self.STATUS_HEADER_RE.search(data).group(0)[8:]
        content_len = self.CONTENT_LENGTH_HEADER_RE.search(data).group(0)[16:]
        remaining = int(content_len) - (len(data) - eoh - len(self.END_OF_HEADER))

        # body sent from csevent_xxx.sock will have id, action, path, & cfg
        while remaining > 0:
            buf = sock.recv(self.MAX_PACKET_SIZE)  # TODO: This will hang things as well.
            if len(buf) == 0:
                break
            data += buf
            remaining -= len(buf)
        body = data[eoh:].decode()
        try:
            result = json.loads(body)
        except json.JSONDecodeError as e:
            # config store receiver doesn't give back
            # proper json for 'put' ops, body
            # contains verbose error message
            # so putting the error msg in result
            result = body.strip()
        return {"status": status_hdr.decode(), "data": result}

    def _receive(self, sock):
        errmsg = None
        result = ""
        try:
            result = self._safe_receive(sock)
        except Exception as err:
            # ignore the command error, continue on to next command
            errmsg = "_receive failed with exception={} err={}".format(type(err), str(err))
        if errmsg is not None:
            self.log(CSCLIENT_NAME, errmsg)
        return result
