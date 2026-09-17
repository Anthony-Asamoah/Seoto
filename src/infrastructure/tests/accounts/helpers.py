from django_otp.oath import TOTP


def current_token(device):
    totp = TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift)
    return format(totp.token(), f'0{device.digits}d')
