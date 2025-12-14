import framebuf
import weather_api
import font_zh
import wifi_manager
import gc

# 5x7 bit patterns for numbers 0-9 and :
BIG_DIGITS = {
    '0': (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    '1': (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    '2': (0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F),
    '3': (0x0E, 0x11, 0x01, 0x06, 0x01, 0x11, 0x0E),
    '4': (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    '5': (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    '6': (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    '7': (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    '8': (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    '9': (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    ':': (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x00),
    ' ': (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
}

def draw_big_char(fb, char, x, y, scale=3):
    if char not in BIG_DIGITS: return
    pattern = BIG_DIGITS[char]
    for row_idx, row_val in enumerate(pattern):
        for col_idx in range(5): 
            if (row_val >> (4 - col_idx)) & 1:
                fb.fill_rect(x + col_idx * scale, y + row_idx * scale, scale, scale, 0x00)

def draw_big_text(fb, text, x, y, scale=3):
    cursor_x = x
    for char in text:
        draw_big_char(fb, char, cursor_x, y, scale)
        cursor_x += (6 * scale) 

def draw_header(fb, date_str, time_str):
    # Top Bar (Date)
    fb.fill_rect(0, 0, 128, 24, 0x00)
    fb.text(date_str, 25, 8, 0xFF)
    
    # Big Time
    draw_big_text(fb, time_str, 19, 40, scale=3)

def draw_footer(fb):
    # System Status
    fb.hline(0, 280, 128, 0x00)
    
    # RAM (Gap Filler)
    mem_free = gc.mem_free() // 1024
    ram_str = f"RAM: {mem_free} KB"
    ram_w = len(ram_str) * 8
    ram_x = (128 - ram_w) // 2
    fb.text(ram_str, ram_x, 240, 0x00)
    
    # IP Address
    ip = wifi_manager.ip_address
    fb.text(ip, 0, 285, 0x00)

def draw_weather(fb):
    # 1. Location: Beijing (Centered)
    font_zh.draw_text(fb, "北京", 48, 90)
    
    # 2. Temp (Centered)
    temp_str = f"{weather_api.cache['temp']} C"
    temp_w = len(temp_str) * 8
    temp_x = (128 - temp_w) // 2
    fb.text(temp_str, temp_x, 108, 0x00)
    
    # 3. Condition (Chinese) (Centered)
    desc = weather_api.cache["desc"]
    desc_w = len(desc) * 16
    desc_x = (128 - desc_w) // 2
    font_zh.draw_text(fb, desc, desc_x, 126)
    
    # 4. Forecast Section
    y_pos = 155
    font_zh.draw_text(fb, "天气预报", 5, y_pos)
    fb.hline(5, y_pos + 18, 118, 0x00)
    
    y_pos += 25
    for day in weather_api.cache.get("forecast", []):
        d_str, t_max, t_min = day
        line = f"{d_str}: {t_min}/{t_max}C"
        fb.text(line, 0, y_pos, 0x00)
        y_pos += 15

def draw_message(fb, message):
    # Draw a box
    fb.rect(5, 90, 118, 180, 0x00)
    font_zh.draw_text(fb, "Message:", 10, 100)
    
    words = message.split(' ')
    y = 130
    x = 10
    for word in words:
        if x + (len(word)*16) > 118:
            x = 10
            y += 20
        font_zh.draw_text(fb, word, x, y)
        x += (len(word) * 16) + 8 

def draw_image(epd, buf):
    try:
        with open('image.bin', 'rb') as f:
            f.readinto(buf)
        # Direct render, skip other drawing
        epd._command(0x4E, bytearray([0x00]))
        epd._command(0x4F, bytearray([0x00, 0x00]))
        epd.set_frame_memory(buf)
        epd.display_frame()
        return True
    except Exception as e:
        print(f"Load Image Error: {e}")
        return False

def draw_screen(epd, time_str, date_str, message=""):
    print(f"Drawing: {time_str} Msg: {message}")
    
    # 1. Clear RAM for the big buffer
    gc.collect()
    
    try:
        # Create a buffer (128 * 296 / 8 = 4736 bytes)
        buf = bytearray(128 * 296 // 8)
        fb = framebuf.FrameBuffer(buf, 128, 296, framebuf.MONO_HLSB)
        
        # --- IMAGE MODE ---
        if message == "__IMAGE__":
            if draw_image(epd, buf):
                return
            else:
                message = "Image Error" # Fallback

        # --- NORMAL MODE ---
        fb.fill(0xFF) # White background

        draw_header(fb, date_str, time_str)
        
        if message:
            draw_message(fb, message)
        else:
            draw_weather(fb)
            
        draw_footer(fb)

        # Send to Display
        epd._command(0x4E, bytearray([0x00]))
        epd._command(0x4F, bytearray([0x00, 0x00]))
        
        epd.set_frame_memory(buf)
        epd.display_frame()
        
    except MemoryError:
        print("Display Error: Out of RAM!")
    finally:
        # Clean up aggressively
        if 'fb' in locals(): del fb
        if 'buf' in locals(): del buf
        gc.collect()