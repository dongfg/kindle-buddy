#!/usr/bin/env python3
"""Offline PW2 clock/calendar; logical landscape, USB socket on the right."""
import argparse
import calendar
import datetime as dt
import fcntl
from functools import lru_cache
import json
import os
from pathlib import Path
import select
import signal
import struct
import subprocess
import sys
import time

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'vendor'))
from lunar_python import Solar
from power_schedule import office_hours, next_morning, prop, suspend_until
FBINK = '/mnt/us/fbink/fbink'
PID = Path('/tmp/kindle-buddy.pid')
FRAME = Path('/tmp/kindle-buddy.png')
W, H = 1024, 758
EXIT = (912, 0, 1024, 112)
running = True


def command(*args, check=False):
    return subprocess.run(args, stdout=subprocess.DEVNULL, check=check)


@lru_cache(maxsize=16)
def font(size, chinese=False):
    name = 'STHeitiMedium.ttf' if chinese else 'Amazon-Ember-Regular.ttf'
    return ImageFont.truetype('/usr/java/lib/fonts/' + name, size)


def centered(draw, box, text, face, fill=0):
    x0, y0, x1, y1 = box
    b = draw.textbbox((0, 0), text, font=face)
    draw.text(((x0+x1-b[2]-b[0])/2, (y0+y1-b[3]-b[1])/2),
              text, font=face, fill=fill)


def month_days(today):
    first = today.replace(day=1)
    start = first - dt.timedelta(days=first.weekday())
    return [start + dt.timedelta(days=i) for i in range(42)]


def battery_status():
    try:
        def read(name):
            return int(subprocess.check_output(
                ['lipc-get-prop', 'com.lab126.powerd', name],
                text=True, timeout=2).strip())
        return max(0, min(100, read('battLevel'))), bool(read('isCharging'))
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def render(now, battery=None):
    image = Image.new('L', (W, H), 255)
    d = ImageDraw.Draw(image)
    centered(d, (32, 32, 392, 192), now.strftime('%H:%M'), font(112))
    if battery is not None:
        level, charging = battery
        shade = 0 if level < 20 else 119
        ink = (shade, shade, shade, 255)
        badge = Image.new('RGBA', (106, 24), (255, 255, 255, 0))
        bd = ImageDraw.Draw(badge)
        bd.rounded_rectangle((1, 5, 29, 20), radius=2, outline=ink, width=1)
        bd.rectangle((30, 10, 32, 15), fill=ink)
        if level:
            bd.rectangle((4, 8, 4+round(22*level/100), 17), fill=ink)
        bd.text((40, 2), '{}%'.format(level), font=font(18), fill=ink)
        if charging:
            bd.polygon(((96,3),(89,13),(95,13),(92,22),(103,10),(97,10)), fill=ink)
        badge = badge.rotate(-45, expand=True, resample=Image.BICUBIC)
        image.paste(badge, (952-badge.width//2, 76-badge.height//2), badge)
    weekday = '一二三四五六日'[now.weekday()]
    label = '{}年{}月{}日 · 周{}'.format(now.year, now.month, now.day, weekday)
    centered(d, (416, 59, 848, 111), label, font(28, True))
    centered(d, (416, 117, 848, 161), lunar_heading(now.date()), font(24, True), 68)
    # Corner badge: the screen edges form the right angle.
    d.line((912, 0, 1023, 111), fill=85, width=2)
    d.line((974, 23, 996, 45), fill=136, width=3)
    d.line((996, 23, 974, 45), fill=136, width=3)
    with Image.open(ROOT/'cat-icon.png') as source:
        cat = source.convert('RGBA')
        cat = cat.crop(cat.getbbox())
        cat.thumbnail((128, 80), Image.LANCZOS)
        image.paste(cat, (880-cat.width//2, 160-cat.height//2), cat)
    d.line((32, 208, 991, 208), fill=0)
    for col, name in enumerate('一二三四五六日'):
        x0, x1 = 32+round(col*960/7), 32+round((col+1)*960/7)
        centered(d, (x0, 224, x1, 264), name, font(24, True))
    d.line((32, 272, 991, 272), fill=0)
    for i, day in enumerate(month_days(now.date())):
        row, col = divmod(i, 7)
        x0, x1 = 32+round(col*960/7), 32+round((col+1)*960/7)
        y0 = 282+row*74
        fill = 0 if day.month == now.month else 136
        if day == now.date():
            cx = (x0+x1)/2
            d.rounded_rectangle((cx-40, y0+4, cx+40, y0+68), radius=12, fill=0)
            fill = 255
        lunar_fill = 255 if day == now.date() else (85 if day.month == now.month else 153)
        # Center the two glyph bounding boxes as one group, with equal outer padding.
        texts = (str(day.day), lunar_labels(day)[1])
        faces = (font(30), font(20, True))
        boxes = [d.textbbox((0, 0), text, font=face) for text, face in zip(texts, faces)]
        heights = [box[3]-box[1] for box in boxes]
        gap = 5
        top = y0+36-(sum(heights)+gap)/2
        for text, face, box, height, color in zip(texts, faces, boxes, heights, (fill, lunar_fill)):
            d.text(((x0+x1-box[2]-box[0])/2, top-box[1]), text, font=face, fill=color)
            top += height+gap
    return image


def display(image, full=False, corner_only=False):
    # Logical right points toward the native bottom edge (USB connector).
    native = image.transpose(Image.ROTATE_270)
    if corner_only:
        native.crop((614, 880, 758, 1024)).save(str(FRAME))
        command(FBINK, '-q', '-w', '-g', 'file='+str(FRAME)+',x=614,y=880', check=True)
    elif full:
        native.save(str(FRAME))
        command(FBINK, '-q', '-f', '-w', '-g', 'file='+str(FRAME), check=True)
    else:
        # Only the logical clock rectangle changes on ordinary minute ticks.
        crop = native.crop((566, 32, 726, 392))
        crop.save(str(FRAME))
        command(FBINK, '-q', '-w', '-g', 'file='+str(FRAME)+',x=566,y=32', check=True)
        native.crop((614, 880, 758, 1024)).save(str(FRAME))
        command(FBINK, '-q', '-w', '-g', 'file='+str(FRAME)+',x=614,y=880', check=True)


def ui_processes():
    for p in Path('/proc').iterdir():
        if p.name.isdigit():
            try:
                name = (p/'comm').read_text().strip()
                status = (p/'status').read_text()
                if name in ('cvm', 'kppMainApp', 'mesquite', 'webreader') and '\nState:\tT' not in status:
                    yield int(p.name)
            except (OSError, UnicodeError):
                pass


def request_stop(*_):
    global running
    running = False


def touch_point(raw_x, raw_y):
    return raw_y, 757-raw_x


@lru_cache(maxsize=128)
def lunar_labels(day):
    lunar = Solar.fromYmd(day.year, day.month, day.day).getLunar()
    month = lunar.getMonthInChinese() + '月'
    date = lunar.getDayInChinese()
    return month + date, month if lunar.getDay() == 1 else date


@lru_cache(maxsize=8)
def lunar_heading(day):
    lunar = Solar.fromYmd(day.year, day.month, day.day).getLunar()
    return '农历 {}{}年 {}'.format(lunar.getYearInGanZhi(), lunar.getYearShengXiao(), lunar_labels(day)[0])


def sleep_screen(target):
    # Static illustration; no clock, wake time, labels or other text.
    with Image.open(ROOT/'sleep-cat.png') as source:
        image = source.convert('L')
        image.thumbnail((W, H), Image.LANCZOS)
        canvas = Image.new('L', (W, H), 255)
        canvas.paste(image, ((W-image.width)//2, (H-image.height)//2))
        return canvas

def drain_power_button(handle):
    data = b''
    while select.select([handle], [], [], 0)[0]:
        data += os.read(handle.fileno(), 4096)
    return data

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        from power_schedule import self_test
        self_test()
        for year in (2024, 2025, 2026):
            for month in range(1, 13):
                day = dt.date(year, month, 15)
                days = month_days(day)
                assert len(days) == 42 and days[0].weekday() == 0 and days[-1].weekday() == 6
                assert sum(d.month == month for d in days) == calendar.monthrange(year, month)[1]
                assert all(b-a == dt.timedelta(days=1) for a, b in zip(days, days[1:]))
        assert touch_point(653, 936) == (936, 104)
        assert lunar_labels(dt.date(2024, 2, 10)) == ('正月初一', '正月')
        assert lunar_labels(dt.date(2025, 1, 29)) == ('正月初一', '正月')
        assert lunar_labels(dt.date(2023, 3, 22)) == ('闰二月初一', '闰二月')
        for stamp in ('2024-02-29T23:59', '2026-12-31T23:59', '2026-11-18T14:08'):
            assert render(dt.datetime.fromisoformat(stamp)).size == (1024, 758)
        print('PASS: 36 month grids, leap year/year boundaries, render cases, touch mapping')
        return
    config_path = ROOT/'config.json'
    config = json.loads(config_path.read_text()) if config_path.exists() else {}
    timezone = dt.timezone(dt.timedelta(hours=config.get('utc_offset_hours', 8)))
    if args.preview:
        render(dt.datetime.now(timezone)).save(str(ROOT/'preview.png'))
        return
    if PID.exists():
        try:
            os.kill(int(PID.read_text()), 0)
        except (ProcessLookupError, ValueError):
            pass
        else:
            raise SystemExit('Already running')
    PID.write_text(str(os.getpid()))
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    paused = []
    touch = None
    grabbed = False
    power_events = None
    power_button = None
    try:
        touch = open('/dev/input/event1', 'rb', buffering=0)
        # Exclusive grab prevents clicks reaching the paused Kindle UI.
        fcntl.ioctl(touch, 0x40044590, 1)
        grabbed = True
        power_button = open('/dev/input/event0', 'rb', buffering=0)
        state = subprocess.check_output(['lipc-get-prop', 'com.lab126.powerd', 'state'], text=True).strip()
        if state != 'active':
            command('lipc-set-prop', 'com.lab126.powerd', 'wakeUp', '1')
        command('lipc-set-prop', 'com.lab126.powerd', 'preventScreenSaver', '1', check=True)
        power_events = subprocess.Popen(
            ['lipc-wait-event', '-m', 'com.lab126.powerd', 'charging,notCharging'],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        for pid in ui_processes():
            try:
                os.kill(pid, signal.SIGSTOP)
                paused.append(pid)
            except ProcessLookupError:
                pass
        previous = None
        refreshes = 0
        next_keepawake = 0
        next_charge_check = 0
        battery = None
        temporary_until = 0
        retry_sleep_after = 0
        ignore_power_until = 0
        power_pressed_at = None
        raw_x = raw_y = None
        tapped_exit = False
        event = struct.Struct('llHHi')
        while running:
            now = dt.datetime.now(timezone)
            schedule = config.get('schedule', {})
            outside = schedule.get('enabled', True) and not office_hours(now, schedule)
            test_file = Path('/tmp/kindle-buddy-sleep-test')
            test_seconds = None
            if test_file.exists():
                try:
                    test_seconds = max(10, min(60, int(test_file.read_text())))
                finally:
                    test_file.unlink(missing_ok=True)
            sleep_request = Path('/tmp/kindle-buddy-sleep-now')
            manual_sleep = power_pressed_at == 'sleep' or sleep_request.exists()
            if sleep_request.exists():
                sleep_request.unlink()
            if (test_seconds or manual_sleep or (outside and time.monotonic() >= temporary_until)) and time.monotonic() >= retry_sleep_after:
                power_pressed_at = None
                target = now + dt.timedelta(seconds=test_seconds) if test_seconds else next_morning(now, schedule)
                try:
                    display(sleep_screen(target), full=True)
                    drain_power_button(power_button)
                    suspend_until(target)
                    wake_keys = drain_power_button(power_button)
                    if wake_keys or manual_sleep:
                        temporary_until = time.monotonic() + schedule.get('manual_wake_minutes', 10)*60
                    # RTC test is one-shot and must return to the normal UI.
                    if test_seconds:
                        temporary_until = time.monotonic() + 60
                    ignore_power_until = time.monotonic()+2
                    previous = None
                    next_keepawake = 0
                    if outside and not wake_keys and not manual_sleep and not test_seconds:
                        # Avoid a busy suspend loop if a wake source prevents sleep.
                        retry_sleep_after = time.monotonic()+5
                        continue
                except (OSError, ValueError, subprocess.SubprocessError, RuntimeError) as error:
                    print('suspend failed; staying awake:', error, flush=True)
                    retry_sleep_after = time.monotonic()+60
                    previous = None
            if time.monotonic() >= next_keepawake:
                command('lipc-set-prop', 'com.lab126.powerd', 'preventScreenSaver', '1', check=True)
                command('lipc-set-prop', 'com.lab126.powerd', 'touchScreenSaverTimeout', '1', check=True)
                next_keepawake = time.monotonic() + 30
            now = dt.datetime.now(timezone)
            minute = now.strftime('%Y-%m-%d %H:%M')
            if minute != previous:
                full = previous is None or previous[:10] != minute[:10] or refreshes % 30 == 0
                battery = battery_status()
                display(render(now, battery), full)
                print('render', minute, 'full' if full else 'clock', flush=True)
                previous = minute
                refreshes += 1
            inputs = [touch, power_button]
            if power_events is not None and power_events.poll() is None:
                inputs.append(power_events.stdout)
            ready = select.select(inputs, [], [], min(1, 60-now.second))[0]
            power_changed = power_events is not None and power_events.stdout in ready
            if power_button in ready:
                data = power_button.read(event.size)
                if len(data) == event.size:
                    _, _, typ, code, value = event.unpack(data)
                    if typ == 1 and code == 116 and time.monotonic() >= ignore_power_until:
                        if value == 1:
                            power_pressed_at = time.monotonic()
                        elif value == 0 and isinstance(power_pressed_at, (int, float)):
                            power_pressed_at = 'sleep' if time.monotonic()-power_pressed_at < 2 else None
            if power_changed:
                os.read(power_events.stdout.fileno(), 4096)
                print('charging event received', flush=True)
            # The event path wakes select immediately. A small status-only poll also
            # covers delayed property updates or an unavailable event listener.
            if power_changed or time.monotonic() >= next_charge_check:
                next_charge_check = time.monotonic() + 2
                try:
                    charging = bool(int(subprocess.check_output(
                        ['lipc-get-prop', 'com.lab126.powerd', 'isCharging'],
                        text=True, timeout=2).strip()))
                    if battery is not None and charging != battery[1]:
                        battery = battery[0], charging  # Percentage remains on minute cadence.
                        display(render(now, battery), corner_only=True)
                        print('charging icon updated:', charging, flush=True)
                except (OSError, ValueError, subprocess.SubprocessError):
                    pass
            if touch in ready:
                data = touch.read(event.size)
                if len(data) != event.size:
                    raise RuntimeError('Touch input ended')
                _, _, typ, code, value = event.unpack(data)
                if typ == 3 and code == 53:
                    raw_x = value
                elif typ == 3 and code == 54:
                    raw_y = value
                elif typ == 3 and code == 57 and value >= 0:
                    raw_x = raw_y = None
                    tapped_exit = False
                elif typ == 0 and code == 0 and raw_x is not None and raw_y is not None:
                    x, y = touch_point(raw_x, raw_y)
                    tapped_exit = EXIT[0] <= x < EXIT[2] and EXIT[1] <= y < EXIT[3]
                elif typ == 3 and code == 57 and value == -1 and tapped_exit:
                    request_stop()
    finally:
        if power_button is not None:
            power_button.close()
        if power_events is not None:
            power_events.terminate()
            try:
                power_events.wait(timeout=2)
            except subprocess.TimeoutExpired:
                power_events.kill()
                power_events.wait()
            power_events.stdout.close()
        if touch:
            try:
                if grabbed:
                    fcntl.ioctl(touch, 0x40044590, 0)
            except OSError:
                pass
            finally:
                touch.close()
        for pid in paused:
            try:
                os.kill(pid, signal.SIGCONT)
            except ProcessLookupError:
                pass
        command('lipc-set-prop', 'com.lab126.powerd', 'preventScreenSaver', '0')
        command('lipc-set-prop', 'com.lab126.appmgrd', 'start', 'app://com.lab126.booklet.settings')
        time.sleep(2)
        command('lipc-set-prop', 'com.lab126.appmgrd', 'start', 'app://com.lab126.booklet.home')
        PID.unlink(missing_ok=True)
        print('Restored Kindle UI', flush=True)


if __name__ == '__main__':
    main()
