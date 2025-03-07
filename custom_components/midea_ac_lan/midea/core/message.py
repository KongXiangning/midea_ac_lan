import logging
from abc import ABC
from enum import IntEnum

_LOGGER = logging.getLogger(__name__)


class MessageLenError(Exception):
    pass


class MessageBodyError(Exception):
    pass


class MessageCheckSumError(Exception):
    pass


class MessageType(IntEnum):
    set = 0x02,
    query = 0x03,
    notify1 = 0x04,
    notify2 = 0x05,
    exception = 0x06,
    querySN = 0x07,
    exception2 = 0x0A,
    querySubtype = 0xA0


class MessageBase(ABC):
    HEADER_LENGTH = 10

    def __init__(self):
        self._device_type = 0x00
        self._message_type = 0x00
        self._body_type = 0x00
        self._device_protocol_version = 0

    @staticmethod
    def checksum(data):
        return (~ sum(data) + 1) & 0xff

    @property
    def header(self):
        raise NotImplementedError

    @property
    def body(self):
        raise NotImplementedError

    @property
    def message_type(self):
        return self._message_type

    @message_type.setter
    def message_type(self, value):
        self._message_type = value

    @property
    def device_type(self):
        return self._device_type

    @device_type.setter
    def device_type(self, value):
        self._device_type = value

    @property
    def body_type(self):
        return self._body_type

    @body_type.setter
    def body_type(self, value):
        self._body_type = value

    @property
    def device_protocol_version(self):
        return self._device_protocol_version

    @device_protocol_version.setter
    def device_protocol_version(self, value):
        self._device_protocol_version = value

    def __str__(self) -> str:
        output = {
            "header": self.header.hex(),
            "body": self.body.hex(),
            "message type": "%02x" % self._message_type,
            "body type": ("%02x" % self._body_type) if self._body_type is not None else "None"
        }
        return str(output)


class MessageRequest(MessageBase):
    def __init__(self, device_protocol_version, device_type, message_type, body_type):
        super().__init__()
        self.device_protocol_version = device_protocol_version
        self.device_type = device_type
        self.message_type = message_type
        self.body_type = body_type

    @property
    def header(self):
        length = self.HEADER_LENGTH + len(self.body)
        return bytearray([
            # flag
            0xAA,
            # length
            length,
            # device type
            self._device_type,
            # frame checksum
            0x00,  # self._device_type ^ length,
            # unused
            0x00, 0x00,
            # frame ID
            0x00,
            # frame protocol version
            0x00,
            # device protocol version
            self._device_protocol_version,
            # frame type
            self._message_type
        ])

    @property
    def _body(self):
        raise NotImplementedError

    @property
    def body(self):
        body = bytearray([])
        if self.body_type is not None:
            body.append(self.body_type)
        if self._body is not None:
            body.extend(self._body)
        return body

    def serialize(self):
        stream = self.header + self.body
        stream.append(MessageBase.checksum(stream[1:]))
        return stream


class MessageQuerySubtype(MessageRequest):
    def __init__(self, device_type):
        super().__init__(
            device_protocol_version=0,
            device_type=device_type,
            message_type=MessageType.querySubtype,
            body_type=0x00)

    @property
    def _body(self):
        return bytearray([0x00] * 18)


class MessageQuestCustom(MessageRequest):
    def __init__(self, device_type, cmd_type, cmd_body):
        super().__init__(
            device_protocol_version=0,
            device_type=device_type,
            message_type=cmd_type,
            body_type=None)
        self._cmd_body = cmd_body

    @property
    def _body(self):
        return bytearray([])

    @property
    def body(self):
        return self._cmd_body


class MessageBody:
    def __init__(self, body):
        self.data = body

    @property
    def body_type(self):
        return self.data[0]

    @staticmethod
    def read_byte(body, byte, default_value=0):
        return body[byte] if len(body) > byte else default_value


class NewProtocolMessageBody(MessageBody):
    def __init__(self, body, bt):
        super().__init__(body)
        if bt == 0xb5:
            self._pack_len = 4
        else:
            self._pack_len = 5

    @staticmethod
    def pack(param, value: bytearray, pack_len=4):
        length = len(value)
        if pack_len == 4:
            stream = bytearray([param & 0xFF, param >> 8, length]) + value
        else:
            stream = bytearray([param & 0xFF, param >> 8, 0x00, length]) + value
        return stream

    def parse(self):
        result = {}
        try:
            pos = 2
            for pack in range(0, self.data[1]):
                param = self.data[pos] + (self.data[pos + 1] << 8)
                if self._pack_len == 5:
                    pos += 1
                length = self.data[pos + 2]
                if length > 0:
                    value = self.data[pos + 3: pos + 3 + length]
                    result[param] = value
                pos += (3 + length)
        except IndexError:
            # Some device used non-standard new-protocol(美的乐享三代中央空调?)
            _LOGGER.debug(f"Non-standard new-protocol {self.data.hex()}")
        return result


class MessageResponse(MessageBase):
    def __init__(self, message):
        super().__init__()
        if message is None or len(message) < self.HEADER_LENGTH + 1:
            raise MessageLenError
        self._header = message[:self.HEADER_LENGTH]
        self.device_protocol_version = self._header[8]
        self.message_type = self._header[-1]
        self.device_type = self._header[2]
        body = message[self.HEADER_LENGTH: -1]
        self._body = MessageBody(body)
        self.body_type = self._body.body_type

    @property
    def header(self):
        return self._header

    @property
    def body(self):
        return self._body.data

    def set_body(self, body: MessageBody):
        self._body = body

    def set_attr(self):
        for key in vars(self._body).keys():
            if key != "data":
                value = getattr(self._body, key, None)
                setattr(self, key, value)


class MessageSubtypeResponse(MessageResponse):
    def __init__(self, message):
        super().__init__(message)
        if self._message_type == MessageType.querySubtype:
            body = message[self.HEADER_LENGTH: -1]
            self.sub_type = (body[2] if len(body) > 2 else 0) + ((body[3] << 8) if len(body) > 3 else 0)

