from datetime import datetime, timezone

class Problem(Exception):
    def __init__(self,message,status=400):
        super().__init__(message)
        self.description=message
        self.code=status


def require(condition, message, status=400):
    if not condition:
        raise Problem(message, status)


def text(value, label, minimum=1, maximum=500):
    require(isinstance(value, str) and minimum <= len(value.strip()) <= maximum, f'{label}: cần {minimum}–{maximum} ký tự.')
    return value.strip()


def integer(value, label, minimum=1, maximum=1000000000):
    require(type(value) is int and minimum <= value <= maximum, f'{label}: phải là số nguyên từ {minimum} đến {maximum}.')
    return value


def boolean(value, label):
    require(type(value) is bool, f'{label}: cần true hoặc false.')
    return int(value)


def timestamp(value):
    value = text(value, 'Thời gian', 10, 40)
    try:
        dt = datetime.fromisoformat(value)
        require(dt.tzinfo is not None, 'Thời gian cần có timezone.')
        return dt.astimezone(timezone.utc).isoformat(timespec='seconds')
    except ValueError:
        require(False, 'Thời gian không hợp lệ.')
