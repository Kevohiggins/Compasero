import ctypes
import time

PULONG = ctypes.POINTER(ctypes.c_ulong)

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PULONG)
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_short),
        ("wParamH", ctypes.c_ushort)
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PULONG)
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT)
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("union", INPUT_UNION)
    ]

INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

VK_CODES = {
    'down': (0x28, True),
    'up': (0x26, True),
    'left': (0x25, True),
    'right': (0x27, True),
    'page down': (0x22, True),
    'pagedown': (0x22, True),
    'page up': (0x21, True),
    'pageup': (0x21, True),
    'space': (0x20, False),
    'espacio': (0x20, False),
    'enter': (0x0D, False),
    'tab': (0x09, False),
    '+': (0x6B, False),
    '-': (0x6D, False),
}

NUMPAD_DUAL_MAP = {
    '0': [0x30, 0x60, 0x2D],
    '1': [0x31, 0x61, 0x23],
    '2': [0x32, 0x62, 0x28],
    '3': [0x33, 0x63, 0x22],
    '4': [0x34, 0x64, 0x25],
    '5': [0x35, 0x65, 0x0C],
    '6': [0x36, 0x66, 0x27],
    '7': [0x37, 0x67, 0x24],
    '8': [0x38, 0x68, 0x26],
    '9': [0x39, 0x69, 0x21],
    '+': [0x6B, 0xBB],
    '-': [0x6D, 0xBD],
    '*': [0x6A],
    '/': [0x6F, 0xBF],
    'enter': [0x0D],
    'space': [0x20],
    'espacio': [0x20],
    't': [0x54],
}

def win32_send_key(key_name):
    key_clean = key_name.lower().strip()
    vk = 0x28
    is_extended = True
    
    if key_clean in VK_CODES:
        vk, is_extended = VK_CODES[key_clean]
    elif len(key_clean) == 1:
        res = ctypes.windll.user32.VkKeyScanW(ord(key_clean))
        if res != -1:
            vk = res & 0xFF
            is_extended = False

    flags_down = KEYEVENTF_EXTENDEDKEY if is_extended else 0
    flags_up = (KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP) if is_extended else KEYEVENTF_KEYUP
    
    x = INPUT()
    x.type = INPUT_KEYBOARD
    x.union.ki.wVk = vk
    x.union.ki.dwFlags = flags_down
    ctypes.windll.user32.SendInput(1, ctypes.byref(x), ctypes.sizeof(x))
    
    time.sleep(0.01)
    
    y = INPUT()
    y.type = INPUT_KEYBOARD
    y.union.ki.wVk = vk
    y.union.ki.dwFlags = flags_up
    ctypes.windll.user32.SendInput(1, ctypes.byref(y), ctypes.sizeof(y))
