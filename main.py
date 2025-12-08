import machine
import framebuf
import il3820
import time

# ESP8266 Pins
spi = machine.SPI(1, baudrate=2000000, polarity=0, phase=0) # Lower speed to be safe
cs = machine.Pin(15, machine.Pin.OUT)
dc = machine.Pin(4, machine.Pin.OUT)
busy = machine.Pin(5, machine.Pin.IN)

epd = il3820.EPD(spi, cs, dc, busy, rst=None)

def main():
    print("Init...")
    epd.init()
    
    # 1. Clear Screen (White)
    print("Filling White...")
    buf = bytearray([0xFF] * (128 * 296 // 8))
    
    # Set X/Y pointers to 0 before writing
    epd._command(0x4E, bytearray([0x00]))
    epd._command(0x4F, bytearray([0x00, 0x00]))
    epd.set_frame_memory(buf)
    epd.display_frame()
    time.sleep(2)

    # 2. Draw Pattern
    print("Drawing Pattern...")
    fb = framebuf.FrameBuffer(buf, 128, 296, framebuf.MONO_HLSB)
    fb.fill(0xFF) # Clear buffer
    
    # Large X
    fb.line(0, 0, 127, 295, 0x00)
    fb.line(127, 0, 0, 295, 0x00)
    
    # Text
    fb.text("TEST", 50, 140, 0x00)
    
    # Reset pointers and write
    epd._command(0x4E, bytearray([0x00]))
    epd._command(0x4F, bytearray([0x00, 0x00]))
    epd.set_frame_memory(buf)
    epd.display_frame()
    
    print("Done.")
    epd.sleep()

if __name__ == "__main__":
    main()
