"""PW2 RTC sleep support and local office-hours policy."""
import datetime as dt
from pathlib import Path
import subprocess
import time


def office_hours(now, config):
    return (now.weekday() in config.get('workdays', [0, 1, 2, 3, 4, 5])
            and config.get('wake_hour', 8) <= now.hour < config.get('sleep_hour', 18))


def next_morning(now, config):
    for offset in range(8):
        candidate = (now + dt.timedelta(days=offset)).replace(
            hour=config.get('wake_hour', 8), minute=0, second=0, microsecond=0)
        if candidate > now and candidate.weekday() in config.get('workdays', [0, 1, 2, 3, 4, 5]):
            return candidate
    raise ValueError('Schedule has no working day')


def prop(name, value=None):
    if value is None:
        return subprocess.check_output(['lipc-get-prop', 'com.lab126.powerd', name],
                                       text=True, timeout=3).strip()
    subprocess.run(['lipc-set-prop', 'com.lab126.powerd', name, str(value)],
                   check=True, timeout=3, stdout=subprocess.DEVNULL)


def suspend_until(target):
    """Only suspend after alarm readback; restore light and clear our alarm on return."""
    alarm = Path('/sys/class/rtc/rtc0/wakealarm')
    brightness = int(prop('flIntensity'))
    epoch = int(target.timestamp())
    if epoch <= time.time()+3:
        raise ValueError('Wake target too close or in the past')
    previous_alarm = alarm.read_text().strip()
    # Do not silently discard another application's earlier wakeup.
    effective = min(epoch, int(previous_alarm)) if previous_alarm and int(previous_alarm) > time.time() else epoch
    armed = False
    try:
        alarm.write_text('0')
        alarm.write_text(str(effective))
        armed = True
        if alarm.read_text().strip() != str(effective):
            raise RuntimeError('RTC alarm readback mismatch; refusing to sleep')
        prop('flIntensity', 0)
        print('suspend: until={} alarm={} brightness={}'.format(target.isoformat(), effective, brightness), flush=True)
        Path('/sys/power/state').write_text('mem')
        print('resume: utc={}'.format(dt.datetime.now(dt.timezone.utc).isoformat()), flush=True)
        if prop('state') != 'active':
            prop('wakeUp', 1)
    finally:
        if armed:
            current = alarm.read_text().strip()
            if current in ('', '0', str(effective)):
                alarm.write_text('0')
                if previous_alarm and int(previous_alarm) > time.time():
                    alarm.write_text(previous_alarm)
        prop('flIntensity', brightness)


def self_test():
    config = {}
    tz = dt.timezone(dt.timedelta(hours=8))
    def stamp(value):
        return dt.datetime.fromisoformat(value).replace(tzinfo=tz)
    assert office_hours(stamp('2026-11-21T08:00'), config)  # Saturday
    assert not office_hours(stamp('2026-11-22T12:00'), config)  # Sunday
    assert not office_hours(stamp('2026-11-18T18:00'), config)
    assert not office_hours(stamp('2026-11-18T07:59'), config)
    assert next_morning(stamp('2026-11-21T18:00'), config) == stamp('2026-11-23T08:00')
    assert next_morning(stamp('2026-11-22T12:00'), config) == stamp('2026-11-23T08:00')
    assert next_morning(stamp('2026-12-31T18:00'), config) == stamp('2027-01-01T08:00')
    print('PASS: office hours, Saturday, Sunday, overnight and year boundary')
