from machine import Pin, ADC, lightsleep
from neopixel import NeoPixel
from time import sleep_ms, ticks_ms, ticks_diff

PIN_CHANGE = Pin.IRQ_FALLING | Pin.IRQ_RISING

speed_input = ADC(Pin(27))
width_input = ADC(Pin(26))
brightness_input = ADC(Pin(28))

pixel_count = 73
np = NeoPixel(Pin(16), pixel_count)
power_btn = Pin(6, Pin.IN, Pin.PULL_UP)

update_delay = 3
color_white = (255, 255, 255)
fade_duration = 750

brightness = 1
animation_delay = 20
led_width = 5

pos = led_width
forward = True
last_update = 0

power_off = False
power_btn_reset = True


def remap(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def scale_color(scale):
    return list(map(lambda x: round(x * scale), color_white))


def update_inputs():
    global brightness, led_width, animation_delay

    brightness_value = brightness_input.read_u16()
    brightness = remap(brightness_value, 0, 65535, 0.01, 1.0)

    width_value = width_input.read_u16()
    led_width = round(remap(width_value, 0, 65535, 1, 12))

    speed_value = speed_input.read_u16()
    animation_delay = round(remap(speed_value, 0, 65535, 500, 7))


def set_lights(color):
    np.fill((0, 0, 0))
    if forward:
        for i in range(pos, max(pos - led_width, -1), -1):
            np[i] = color
    else:
        for i in range(pos, min(pos + led_width, pixel_count)):
            np[i] = color


def move_lights():
    global forward, pos
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


def is_centered():
    if forward:
        return pos == (pixel_count + led_width) // 2
    else:
        return pos == (pixel_count - led_width) // 2 + 1


def low_power(immdeiate):
    global last_update, forward, pos, power_off

    def power_btn_change(_):
        global power_off, power_btn_reset
        if power_btn.value() == 1:
            power_btn_reset = True
        elif power_btn_reset:
            power_off = False
            power_btn_reset = False

    power_btn.irq(handler=power_btn_change, trigger=PIN_CHANGE)
    if not immdeiate:
        ratio = 1
        while not is_centered():
            update_inputs()

            move_lights()
            set_lights(scale_color(brightness))

            np.write()
            sleep_ms(min(round(animation_delay * ratio), 85))
            ratio *= 1.05

        forward = True
        start = ticks_ms()

        while ticks_diff(ticks_ms(), start) < fade_duration:
            update_inputs()
            pos = (pixel_count + led_width) // 2

            ratio = ticks_diff(ticks_ms(), start) / fade_duration
            scaled_color = scale_color((1 - ratio) * brightness)

            set_lights(scaled_color)
            np.write()

            sleep_ms(5)

    np.fill((0, 0, 0))
    np.write()

    power_off = True
    while power_off:
        lightsleep(60000)
    power_btn.irq(handler=None)

    forward = True
    start = ticks_ms()

    while ticks_diff(ticks_ms(), start) < fade_duration:
        update_inputs()
        pos = (pixel_count + led_width) // 2

        ratio = ticks_diff(ticks_ms(), start) / fade_duration
        scaled_color = scale_color(ratio * brightness)

        set_lights(scaled_color)
        np.write()

        sleep_ms(5)

    last_update = ticks_ms()


np.fill((0, 0, 0))
np.write()

update_inputs()
low_power(True)

while True:
    update_inputs()

    now = ticks_ms()
    while ticks_diff(now, last_update) >= animation_delay:
        last_update += animation_delay
        move_lights()

    set_lights(scale_color(brightness))
    np.write()

    if power_btn.value() == 1:
        sleep_ms(update_delay)
        power_btn_reset = True
    elif power_btn_reset:
        power_btn_reset = False
        low_power(False)
