import time

# Display resolution
EPD_WIDTH = 128
EPD_HEIGHT = 296


class EPD:
    def __init__(self, spi, cs, dc, busy, rst=None):
        self.spi = spi
        self.cs = cs
        self.dc = dc
        self.busy = busy
        self.rst = rst

        self.cs.init(self.cs.OUT, value=1)
        self.dc.init(self.dc.OUT, value=0)
        if self.busy:
            self.busy.init(self.busy.IN)
        if self.rst:
            self.rst.init(self.rst.OUT, value=0)

        self.width = EPD_WIDTH
        self.height = EPD_HEIGHT

    def _command(self, command, data=None):
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([command]))
        self.cs(1)
        if data is not None:
            self._data(data)

    def _data(self, data):
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(data)
        self.cs(1)

    def init(self):
        # Hardware reset
        if self.rst:
            self.rst(1)
            time.sleep_ms(200)  # type: ignore
            self.rst(0)
            time.sleep_ms(200)  # type: ignore
            self.rst(1)
            time.sleep_ms(200)  # type: ignore

        self._command(0x12)  # SWRESET
        self.wait_until_idle()

        self._command(
            0x01,
            bytearray([(EPD_HEIGHT - 1) & 0xFF, ((EPD_HEIGHT - 1) >> 8) & 0xFF, 0x00]),
        )  # Driver output control
        self._command(0x11, bytearray([0x03]))  # Data entry mode
        self._command(
            0x44, bytearray([0x00, (EPD_WIDTH // 8) - 1])
        )  # Set Ram-X address start/end position
        self._command(
            0x45,
            bytearray(
                [0x00, 0x00, (EPD_HEIGHT - 1) & 0xFF, ((EPD_HEIGHT - 1) >> 8) & 0xFF]
            ),
        )  # Set Ram-Y address start/end position
        self._command(0x3C, bytearray([0x05]))  # BorderWaveform
        self._command(0x21, bytearray([0x00, 0x80]))  #  Display update control
        self._command(0x18, bytearray([0x80]))  # Read built-in temperature sensor
        self.wait_until_idle()

    def wait_until_idle(self):
        if self.busy:
            while self.busy.value() == 1:
                time.sleep_ms(50)  # type: ignore
        else:
            time.sleep_ms(2000)  # type: ignore

    def set_frame_memory(self, image):
        self._command(0x24)  # WRITE_RAM
        self._data(image)

    def display_frame(self):
        self._command(0x22, bytearray([0xF7]))
        self._command(0x20)
        self.wait_until_idle()

    def sleep(self):
        self._command(0x10, bytearray([0x01]))
