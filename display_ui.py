import framebuf
import weather_api

def draw_screen(epd, time_str, date_str):
    print(f"Drawing: {time_str}")
    
    # Create a buffer (128 * 296 / 8 = 4736 bytes)
    buf = bytearray(128 * 296 // 8)
    fb = framebuf.FrameBuffer(buf, 128, 296, framebuf.MONO_HLSB)
    fb.fill(0xFF) # White background

    # Top Bar (Date)
    fb.fill_rect(0, 0, 128, 24, 0x00)
    fb.text(date_str, 25, 8, 0xFF)

    # Big Time (Simulated by drawing twice)
    fb.text(time_str, 30, 50, 0x00)
    fb.text(time_str, 31, 50, 0x00)

    # Weather Box
    fb.rect(10, 80, 108, 60, 0x00)
    fb.text("Beijing", 15, 90, 0x00)
    fb.text(f"{weather_api.cache['temp']} C", 15, 105, 0x00)
    fb.text(str(weather_api.cache["desc"]), 15, 120, 0x00)

    # Send to Display
    # Note: Accessing private methods of epd (starting with _) is common in MicroPython drivers
    # but theoretically we should check if public methods exist. 
    # The `il3820` driver we wrote uses set_frame_memory / display_frame.
    
    # Reset pointers
    epd._command(0x4E, bytearray([0x00]))
    epd._command(0x4F, bytearray([0x00, 0x00]))
    
    epd.set_frame_memory(buf)
    epd.display_frame()
