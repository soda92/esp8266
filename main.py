import machine
import time

# Configuration
# GPIO 4 is Pin D2 on NodeMCU/WeMos D1 Mini
PIN_NUM = 4

# Initialize PWM for the buzzer
# PWM allows us to change frequency (pitch) for passive buzzers
# or just turn it on/off for active buzzers.
try:
    buzzer = machine.PWM(machine.Pin(PIN_NUM))
except Exception as e:
    print(f"Error initializing PWM: {e}")
    # Fallback to simple GPIO if PWM fails (rare)
    buzzer = machine.Pin(PIN_NUM, machine.Pin.OUT)

def quiet():
    """Silence the buzzer."""
    if isinstance(buzzer, machine.PWM):
        buzzer.duty(0)
    else:
        buzzer.value(0)

def beep(freq=1000, duration_ms=100):
    """Play a beep."""
    if isinstance(buzzer, machine.PWM):
        buzzer.freq(freq)      # Set pitch
        buzzer.duty(512)       # Set volume/power (512 is 50%)
    else:
        buzzer.value(1)        # Simple ON
    
    time.sleep_ms(duration_ms)
    quiet()

def main():
    print("Initializing...")
    quiet() # Ensure it starts silent
    time.sleep(1) # Wait a second
    
    print("Looping beeps...")
    while True:
        # Beep 1: Low pitch
        beep(freq=800, duration_ms=200)
        time.sleep_ms(300)
        
        # Beep 2: High pitch
        beep(freq=1200, duration_ms=200)
        time.sleep_ms(800)

if __name__ == "__main__":
    main()