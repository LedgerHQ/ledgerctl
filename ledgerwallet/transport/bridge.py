import base64
import json

import falcon
import hid as hid


LEDGER_VENDOR_ID = 0x2c97


class HidDevice(object):
    def __init__(self, device):
        self.device = device
        self.opened = True

    def write(self, data):
        # data is prefixed by its size
        data_to_send = int.to_bytes(len(data), 2, 'big') + data
        offset = 0
        seq_idx = 0
        while offset < len(data_to_send):
            # Header: channel (0x101), tag (0x05), sequence index
            header = b'\x01\x01\x05' + seq_idx.to_bytes(2, 'big')
            pkt_data = header + data_to_send[offset:offset + 64 - len(header)]

            self.device.write(b'\x00' + pkt_data)
            offset += 64 - len(header)
            seq_idx += 1

    def read(self, timeout: int) -> bytes:
        seq_idx = 0

        self.device.set_nonblocking(False)
        data_chunk = bytes(self.device.read(64 + 1))
        self.device.set_nonblocking(True)

        assert data_chunk[:2] == b"\x01\x01"
        assert data_chunk[2] == 5
        assert data_chunk[3:5] == seq_idx.to_bytes(2, 'big')

        data_len = int.from_bytes(data_chunk[5:7], 'big')
        data = data_chunk[7:]

        while len(data) < data_len:
            read_bytes = bytes(self.device.read(64 + 1, timeout_ms=timeout))
            data += read_bytes[5:]

        return data[:data_len]

    def exchange(self, data: bytes, timeout=1000):
        self.write(data)
        return self.read(timeout)

    def close(self):
        if self.opened:
            try:
                self.device.close()
            except:
                pass
        self.opened = False


class CommException(Exception):
    def __init__(self, message, sw=0x6f00, data=None):
        self.message = message
        self.sw = sw
        self.data = data

    def __str__(self):
        buf = "Exception : " + self.message
        return buf


DEVICE = None  # type: HidDevice


class OpenResource:
    def on_post(self, req, resp):
        global DEVICE

        body = req.stream.read()
        if not body:
            raise falcon.HTTPBadRequest('Empty request body',
                                        'A valid JSON document is required.')
        try:
            req.context['doc'] = json.loads(body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            raise falcon.HTTPError(falcon.HTTP_753,
                                   'Malformed JSON',
                                   'Could not decode the request body. The '
                                   'JSON was incorrect or not encoded as '
                                   'UTF-8.')
        doc = req.context['doc']

        dev = hid.device()
        dev.open_path(base64.b64decode(doc['path']))
        dev.set_nonblocking(True)
        DEVICE = HidDevice(dev)


class ReadResource:
    def on_get(self, req, resp):
        global DEVICE
        resp.media = {'data': DEVICE.read(1000).hex()}


class WriteResource:
    def on_post(self, req, resp):
        global DEVICE

        body = req.stream.read()
        if not body:
            raise falcon.HTTPBadRequest('Empty request body',
                                        'A valid JSON document is required.')
        try:
            req.context['doc'] = json.loads(body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            raise falcon.HTTPError(falcon.HTTP_753,
                                   'Malformed JSON',
                                   'Could not decode the request body. The '
                                   'JSON was incorrect or not encoded as '
                                   'UTF-8.')
        data = bytes.fromhex(req.context['doc']['data'])
        print("Wriring " + data.hex())
        DEVICE.write(data)


class EnumerateResource:
    def on_get(self, req, resp):
        """Handles GET requests"""
        devices = []

        # hid_device_path = None
        for hidDevice in hid.enumerate(LEDGER_VENDOR_ID, 0):
            if ('interface_number' in hidDevice and hidDevice['interface_number'] == 0) or (
                    'usage_page' in hidDevice and hidDevice['usage_page'] == 0xffa0):

                hid_device_path = hidDevice['path']
                devices.append(base64.b64encode(hid_device_path).decode())
        resp.media = {"devices": devices}


api = falcon.API()
api.add_route('/enumerate', EnumerateResource())
api.add_route('/open', OpenResource())
api.add_route('/write', WriteResource())
api.add_route('/read', ReadResource())
