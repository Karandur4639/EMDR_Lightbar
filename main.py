from machine import Pin, ADC, lightsleep, deepsleep
from neopixel import NeoPixel
from time import sleep_ms, ticks_ms, ticks_diff
from sys import maxsize

speed_input = ADC(Pin(27))
width_input = ADC(Pin(26))
brightness_input = ADC(Pin(28))
power_btn = Pin(6, Pin.IN, Pin.PULL_UP)

pixel_count = 73
np = NeoPixel(Pin(16), pixel_count)

update_delay = 3
color_white = (255, 255, 255)

brightness = 1
animation_delay = 20
led_width = 5

pos = led_width
forward = True
last_update = ticks_ms()

power_off = False
power_btn_reset = True


def remap(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def scale_color():
    return list(map(lambda x: round(x * brightness), color_white))


def update_brightness():
    global brightness
    brightness_value = brightness_input.read_u16()
    brightness = remap(brightness_value, 0, 65535, 0.01, 1.0)


def update_width():
    global led_width
    width_value = width_input.read_u16()
    led_width = round(remap(width_value, 0, 65535, 1, 12))


def update_speed():
    global animation_delay
    speed_value = speed_input.read_u16()
    animation_delay = round(remap(speed_value, 0, 65535, 500, 5))


def low_power():
    global last_update, forward, pos, power_off

    def power_btn_change(_):
        global power_off, power_btn_reset
        if power_btn.value() == 1:
            power_btn_reset = True
        elif power_btn_reset:
            power_off = False
            power_btn_reset = False

    power_btn.irq(handler=power_btn_change, trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING)
    power_off = True

    np.fill((0, 0, 0))
    np.write()

    while power_off:
        lightsleep(60000)
    power_btn.irq(handler=None)

    last_update = ticks_ms()
    forward = True
    pos = pixel_count // 2 + led_width // 2


np.fill((0, 0, 0))
np.write()
low_power()

while True:
    now = ticks_ms()
    while ticks_diff(now, last_update) >= animation_delay:
        last_update += animation_delay

        if forward:
            pos += 1
            if pos == pixel_count - 1:
                forward = False
                pos = pixel_count - led_width
        else:
            pos -= 1
            if pos == 0:
                forward = True
                pos = led_width - 1

    if forward:
        np.fill((0, 0, 0))
        for i in range(pos, max(pos - led_width, -1), -1):
            np[i] = scale_color()
    else:
        np.fill((0, 0, 0))
        for i in range(pos, min(pos + led_width, pixel_count)):
            np[i] = scale_color()

    update_speed()
    update_width()
    update_brightness()
    np.write()

    if power_btn.value() == 1:
        sleep_ms(update_delay)
        power_btn_reset = True
    elif power_btn_reset:
        power_btn_reset = False
        low_power()
