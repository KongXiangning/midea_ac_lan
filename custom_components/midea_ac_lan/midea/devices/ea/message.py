from ...core.message import (
    MessageType,
    MessageRequest,
    MessageResponse,
    MessageBody,
)


class MessageECBase(MessageRequest):
    def __init__(self, device_protocol_version, message_type, body_type):
        super().__init__(
            device_protocol_version=device_protocol_version,
            device_type=0xEA,
            message_type=message_type,
            body_type=body_type
        )

    @property
    def _body(self):
        raise NotImplementedError


class MessageQuery(MessageECBase):
    def __init__(self, device_protocol_version):
        super().__init__(
            device_protocol_version=device_protocol_version,
            message_type=MessageType.query,
            body_type=None)

    @property
    def body(self):
        return bytearray([
            0xAA, 0x55, self._device_protocol_version, 0x03, 0x00
        ])

    @property
    def _body(self):
        return bytearray([])


class EABody1(MessageBody):
    def __init__(self, body):
        super().__init__(body)
        self.mode = body[6] + (body[7] << 8)
        self.progress = body[14]
        self.cooking = self.progress == 2
        self.keep_warm = self.progress == 3
        self.top_temperature = body[18]
        self.bottom_temperature = body[19]
        self.time_remaining = body[22] * 60 + body[23]
        self.keep_warm_time = body[26] * 60 + body[27]


class EABody2(MessageBody):
    def __init__(self, body):
        super().__init__(body)
        self.progress = body[9]
        self.cooking = self.progress == 2
        self.keep_warm = self.progress == 3
        self.mode = body[58] + (body[59] << 8)
        self.time_remaining = body[50] * 60 + body[51]
        self.keep_warm_time = body[54] * 60 + body[55]
        self.top_temperature = body[21]
        self.bottom_temperature = body[20]


class EABody3(MessageBody):
    def __init__(self, body):
        super().__init__(body)
        self.mode = body[4] + (body[5] << 8)
        self.progress = body[8]
        self.cooking = self.progress == 2
        self.keep_warm = self.progress == 3
        self.time_remaining = body[12] * 60 + body[13]
        self.top_temperature = body[20]
        self.bottom_temperature = body[21]
        self.keep_warm_time = body[22] * 60 + body[23]


class MessageEAResponse(MessageResponse):
    def __init__(self, message):
        super().__init__(message)
        if self._device_protocol_version == 0:
            if self._message_type == MessageType.set and super().body[5] == 0x16:  # 381
                self.set_body(EABody1(super().body))
            elif self._message_type == MessageType.query:
                if super().body[6] == 0x52 and super().body[7] == 0xc3:  # 404
                    self.set_body(EABody2(super().body))
                elif super().body[5] == 0x3d:  # 420
                    self.set_body(EABody1(super().body))
            elif self._message_type == MessageType.notify1 and super().body[5] == 0x3d:  # 463
                self.set_body(EABody1(super().body))
        else:
            if(self._message_type == MessageType.set and super().body[3] == 0x02) or \
                    (self._message_type == MessageType.query and super().body[3] == 0x03) or \
                    (self._message_type == MessageType.notify1 and super().body[3] == 0x04):  # 351
                self.set_body(EABody3(super().body))
            elif self._message_type == MessageType.notify1 and super().body[3] == 0x06:
                self.mode = super().body[4] + (super().body[5] << 8)
        self.set_attr()
