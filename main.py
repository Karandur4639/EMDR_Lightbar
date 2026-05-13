from machine import Pin, ADC, lightsleep
from neopixel import NeoPixel
from time import sleep_ms, ticks_ms, ticks_diff, ticks_add
from math import log, floor

PIN_CHANGE = Pin.IRQ_FALLING | Pin.IRQ_RISING

speed_input = ADC(Pin(27))
width_input = ADC(Pin(26))
brightness_input = ADC(Pin(28))

pixel_count = 73
np = NeoPixel(Pin(22), pixel_count)
power_btn = Pin(9, Pin.IN, Pin.PULL_UP)
np_enable = Pin(21, Pin.OUT)

update_delay = 2
color_white = (255, 255, 255)
fade_duration = 750

brightness = 1
animation_delay = 20
led_width = 5

fade_delay = 5
speed_decay = 0.02
max_slow_multiplier = 4

pos = 0
forward = True
last_update = 0

power_off = False
power_btn_reset = True


def remap(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def linearize_log(value, min_val=325, max_val=65535, curve=10):
    clamped = max(min(value, max_val), min_val)
    normalized = (clamped - min_val) / (max_val - min_val)
    return log(1 + normalized * (curve - 1)) / log(curve) * max_val


def scale_color(scale):
    return list(map(lambda x: round(x * scale), color_white))


def update_inputs():
    global brightness, led_width, animation_delay
    updated = False

    brightness_value = brightness_input.read_u16()
    new_brightness = remap(brightness_value, 0, 65535, 0.01, 1)
    if new_brightness != brightness:
        updated = True
        brightness = new_brightness

    width_value = linearize_log(width_input.read_u16())
    new_led_width = round(remap(width_value, 0, 65535, 1, 12))
    if new_led_width != led_width:
        updated = True
        led_width = new_led_width

    speed_value = linearize_log(speed_input.read_u16())
    new_animation_delay = round(remap(speed_value, 0, 65535, 85, 4))
    if new_animation_delay != animation_delay:
        updated = True
        animation_delay = new_animation_delay

    return updated


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


def get_centered_pos():
    if forward:
        return (pixel_count + led_width) // 2 - 1
    else:
        return (pixel_count - led_width) // 2


def is_centered():
    return pos == get_centered_pos()


def animate(delay=None):
    global last_update

    has_changes = update_inputs()
    frames = 0

    if delay is None:
        delay = animation_delay

    now = ticks_ms()
    while ticks_diff(now, last_update) >= delay:
        has_changes = True
        last_update = ticks_add(last_update, delay)
        frames += 1
        move_lights()

    if has_changes:
        set_lights(scale_color(brightness))
        np.write()

    return frames


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
        last_forward = forward
        bounces_remaining = 4
        ratio = 1

        while bounces_remaining > 0:
            frames = animate(round(min(animation_delay * ratio, animation_delay * max_slow_multiplier)))

            if last_forward != forward:
                last_forward = forward
                bounces_remaining -= 1

            if bounces_remaining == 1:
                for _ in range(frames):
                    ratio += speed_decay

            sleep_ms(update_delay)

        while not is_centered():
            update_inputs()

            move_lights()
            set_lights(scale_color(brightness))

            np.write()
            ratio += speed_decay
            sleep_ms(round(min(animation_delay * ratio, animation_delay * max_slow_multiplier)))

        start = ticks_ms()
        while ticks_diff(ticks_ms(), start) < fade_duration:
            update_inputs()

            ratio = ticks_diff(ticks_ms(), start) / fade_duration
            scaled_color = scale_color((1 - ratio) * brightness)

            set_lights(scaled_color)
            np.write()

            sleep_ms(fade_delay)

    np.fill((0, 0, 0))
    np.write()
    np_enable.low()

    power_off = True
    while power_off:
        lightsleep(60000)

    power_btn.irq(handler=None)
    np_enable.high()

    start = ticks_ms()
    pos = get_centered_pos()

    while ticks_diff(ticks_ms(), start) < fade_duration:
        update_inputs()

        ratio = ticks_diff(ticks_ms(), start) / fade_duration
        scaled_color = scale_color(ratio * brightness)

        set_lights(scaled_color)
        np.write()

        sleep_ms(fade_delay)

    last_update = ticks_ms()


np_enable.high()
np.fill((0, 0, 0))
np.write()

update_inputs()
low_power(True)

while True:
    animate()

    if power_btn.value() == 1:
        sleep_ms(update_delay)
        power_btn_reset = True
    elif power_btn_reset:
        power_btn_reset = False
        low_power(False)
