from ...core.message import (
    MessageType,
    MessageRequest,
    MessageResponse,
    MessageBody,
)


class MessageE1Base(MessageRequest):
    def __init__(self, device_protocol_version, message_type, body_type):
        super().__init__(
            device_protocol_version=device_protocol_version,
            device_type=0xE1,
            message_type=message_type,
            body_type=body_type
        )

    @property
    def _body(self):
        raise NotImplementedError


class MessagePower(MessageE1Base):
    def __init__(self, device_protocol_version):
        super().__init__(
            device_protocol_version=device_protocol_version,
            message_type=MessageType.set,
            body_type=0x08)
        self.power = False

    @property
    def _body(self):
        power = 0x01 if self.power else 0x00
        return bytearray([
            power,
            0x00, 0x00, 0x00
        ])


class MessageLock(MessageE1Base):
    def __init__(self, device_protocol_version):
        super().__init__(
            device_protocol_version=device_protocol_version,
            message_type=MessageType.set,
            body_type=0x83)
        self.lock = False

    @property
    def _body(self):
        lock = 0x03 if self.lock else 0x04
        return bytearray([lock]) + bytearray([0x00] * 36)


class MessageStorage(MessageE1Base):
    def __init__(self, device_protocol_version):
        super().__init__(
            device_protocol_version=device_protocol_version,
            message_type=MessageType.set,
            body_type=0x81)
        self.storage = False

    @property
    def _body(self):
        storage = 0x01 if self.storage else 0x00
        return bytearray([0x00, 0x00, 0x00, storage]) + \
            bytearray([0xff] * 6) + bytearray([0x00] * 27)


class MessageQuery(MessageE1Base):
    def __init__(self, device_protocol_version):
        super().__init__(
            device_protocol_version=device_protocol_version,
            message_type=MessageType.query,
            body_type=0x00)

    @property
    def _body(self):
        return bytearray([])


class E1GeneralMessageBody(MessageBody):
    def __init__(self, body):
        super().__init__(body)
        self.power = body[1] > 0
        self.status = body[1]
        self.mode = body[2]
        self.additional = body[3]
        self.door = (body[5] & 0x01) == 0       # 0 - open, 1 - close
        self.rinse_aid = (body[5] & 0x02) > 0   # 0 - enough, 1 - shortage
        self.salt = (body[5] & 0x04) > 0        # 0 - enough, 1 - shortage
        start_pause = (body[5] & 0x08) > 0
        if start_pause:
            self.start = True
        elif self.status in [2, 3]:
            self.start = False
        self.child_lock = (body[5] & 0x10) > 0
        self.uv = (body[4] & 0x2) > 0
        self.dry = (body[4] & 0x10) > 0
        self.dry_status = (body[4] & 0x20) > 0
        self.storage = (body[5] & 0x20) > 0
        self.storage_status = (body[5] & 0x40) > 0
        self.time_remaining = body[6]
        self.progress = body[9]
        self.storage_remaining = body[18] if len(body) > 18 else False
        self.temperature = body[11]
        self.humidity = body[33] if len(body) > 33 else None
        self.waterswitch = (body[4] & 0x4) > 0
        self.water_lack = (body[5] & 0x80) > 0
        self.error_code = body[10]
        self.softwater = body[13]
        self.wrong_operation = body[16]
        self.bright = body[24]


class MessageE1Response(MessageResponse):
    def __init__(self, message):
        super().__init__(message)
        if (self._message_type == MessageType.set and 0 <= self._body_type <= 7) or \
                (self._message_type in [MessageType.query, MessageType.notify1] and self._body_type == 0):
            self.set_body(E1GeneralMessageBody(super().body))
        self.set_attr()
