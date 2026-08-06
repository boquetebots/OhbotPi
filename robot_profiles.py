#!/usr/bin/env python3
"""
Robot Calibration Profiles
==========================

Lets one set of code drive several different Ohbot/Yobot heads, each with
its own motor calibration.

THE IDEA, IN PLAIN ENGLISH
--------------------------
Every part of this project reads its motor numbers from ONE file:

    ohbotData/MotorDefinitionsv21.omd

That never changes. This module doesn't try to make the rest of the code
clever about multiple robots. Instead it keeps a little library of saved
calibrations:

    ohbotData/robots/Goldie.omd
    ohbotData/robots/Blue Boy.omd
    ...

"Saving" a robot = copy the live file into that library under a name.
"Loading" a robot = copy that named file back over the live file.

So at any moment the live file holds exactly one robot's numbers, and
everything downstream — the greeter, the GUI, the timeline — carries on
none the wiser. Nothing else in the codebase had to change.

WHICH ROBOT IS "ACTIVE"
-----------------------
A one-line text file remembers the name of the last robot loaded or saved:

    ohbotData/active_robot.txt

This is a LABEL ONLY, so pages can display "Currently loaded: Goldie".
No motor code reads it. If it goes missing or says something wrong, the
robot still moves correctly — the live .omd file is always the truth.

THE ONE THING TO KNOW
---------------------
Programs read the .omd file once, when they start. So loading a different
robot while the greeter or the GUI is running does nothing until that
program is restarted. The launcher page enforces this by refusing to switch
robots while something is running.
"""

import os
import re
import shutil
from datetime import datetime

from lxml import etree

# ── Where everything lives ────────────────────────────────────────────────
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
OHBOT_DATA     = os.path.join(BASE_DIR, 'ohbotData')
ROBOTS_DIR     = os.path.join(OHBOT_DATA, 'robots')
MOTOR_DEF_FILE = os.path.join(OHBOT_DATA, 'MotorDefinitionsv21.omd')
ACTIVE_FILE    = os.path.join(OHBOT_DATA, 'active_robot.txt')

# The 8 motor indexes a valid file must contain — same set the calibration
# page and gui_server use. Guards against loading a truncated or foreign file.
EXPECTED_MOTORS = {0, 1, 2, 3, 4, 5, 6, 7}

MAX_NAME_LEN = 40


# ── Names ─────────────────────────────────────────────────────────────────

def clean_name(name):
    """
    Turn whatever the user typed into something safe to use as a filename,
    while still looking like what they typed.

    Keeps letters, numbers, spaces, dashes and underscores. Throws away
    anything else (slashes, dots, quotes) that could escape the folder or
    confuse the file system.

    Returns the cleaned name, or None if nothing usable is left.
    """
    if not name:
        return None
    name = str(name).strip()
    name = re.sub(r'[^A-Za-z0-9 _-]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    if not name:
        return None
    return name[:MAX_NAME_LEN]


def profile_path(name):
    """Full path to a named robot's file. Assumes `name` is already cleaned."""
    return os.path.join(ROBOTS_DIR, f'{name}.omd')


# ── Validation ────────────────────────────────────────────────────────────

def check_omd(path):
    """
    Make sure a file really is a usable motor definitions file before we let
    it anywhere near the live file.

    Returns (ok, message_or_None, three_point_motor_names).
    """
    try:
        tree = etree.parse(path)
    except Exception as e:
        return False, f'Not a readable motor file: {e}', []

    root = tree.getroot()
    if root.tag != 'Motors':
        return False, 'File does not look like a motor definitions file.', []

    found = set()
    three_point = []
    for child in root:
        m = child.get('Motor')
        if m is None:
            return False, 'A motor entry has no Motor number.', []
        found.add(int(m))
        if child.get('Center') is not None:
            three_point.append(child.get('Name') or f'Motor {m}')

    if found != EXPECTED_MOTORS:
        missing = sorted(EXPECTED_MOTORS - found)
        return False, (f'File does not have the expected 8 motors '
                       f'(missing motor numbers: {missing}).'), []

    return True, None, three_point


# ── Active robot label ────────────────────────────────────────────────────

def get_active():
    """Name of the robot last loaded or saved, or None if never set."""
    try:
        with open(ACTIVE_FILE, 'r') as f:
            return clean_name(f.read())
    except Exception:
        return None


def set_active(name):
    try:
        os.makedirs(OHBOT_DATA, exist_ok=True)
        with open(ACTIVE_FILE, 'w') as f:
            f.write(name or '')
        return True
    except Exception:
        return False


# ── Listing ───────────────────────────────────────────────────────────────

def list_robots():
    """
    Every saved robot, newest first.

    Each entry: name, when it was saved, and how many motors in it have been
    three-point calibrated (a Center attribute) — handy for spotting a robot
    still on the old two-point numbers.
    """
    os.makedirs(ROBOTS_DIR, exist_ok=True)
    out = []
    for fn in os.listdir(ROBOTS_DIR):
        if not fn.endswith('.omd'):
            continue
        path = os.path.join(ROBOTS_DIR, fn)
        ok, err, three_point = check_omd(path)
        stamp = os.path.getmtime(path)
        out.append({
            'name': fn[:-4],
            'saved': datetime.fromtimestamp(stamp).strftime('%d %b %Y, %H:%M'),
            'saved_epoch': stamp,
            'valid': ok,
            'problem': err,
            'three_point_count': len(three_point),
        })
    out.sort(key=lambda r: r['saved_epoch'], reverse=True)
    return out


# ── Backups ───────────────────────────────────────────────────────────────

def _next_backup_name():
    """Same MD_old_N.omd numbering the calibration page already uses, so all
    the safety copies sit together in one place."""
    n = 1
    while os.path.exists(os.path.join(OHBOT_DATA, f'MD_old_{n}.omd')):
        n += 1
    return f'MD_old_{n}.omd'


def backup_live_file():
    """Copy the current live file to ohbotData/MD_old_N.omd. Returns the
    backup's filename, or None if there was no live file to copy."""
    if not os.path.exists(MOTOR_DEF_FILE):
        return None
    name = _next_backup_name()
    shutil.copy2(MOTOR_DEF_FILE, os.path.join(OHBOT_DATA, name))
    return name


# ── Save / Load / Delete ──────────────────────────────────────────────────

def save_profile(raw_name, overwrite=True):
    """
    Copy the live motor file into the robot library under `raw_name`.

    Returns (ok, result_dict_or_error_string).
    """
    name = clean_name(raw_name)
    if not name:
        return False, ('Please give the robot a name — letters, numbers, '
                       'spaces, dashes and underscores only.')

    if not os.path.exists(MOTOR_DEF_FILE):
        return False, ('There is no live motor file to save yet '
                       f'({MOTOR_DEF_FILE} is missing).')

    ok, err, three_point = check_omd(MOTOR_DEF_FILE)
    if not ok:
        return False, f'The live motor file is not valid, so it was not saved: {err}'

    os.makedirs(ROBOTS_DIR, exist_ok=True)
    dest = profile_path(name)
    replaced = os.path.exists(dest)
    if replaced and not overwrite:
        return False, f'A robot called "{name}" already exists.'

    # If we're about to overwrite an existing robot, keep a dated copy of the
    # old one rather than losing it outright.
    previous_backup = None
    if replaced:
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        previous_backup = f'{name}.{stamp}.omd.bak'
        shutil.copy2(dest, os.path.join(ROBOTS_DIR, previous_backup))

    shutil.copy2(MOTOR_DEF_FILE, dest)
    set_active(name)

    return True, {
        'name': name,
        'replaced': replaced,
        'previous_backup': previous_backup,
        'three_point_count': len(three_point),
    }


def load_profile(raw_name):
    """
    Copy a saved robot's file over the live motor file, so everything that
    starts from now on uses that robot's calibration.

    The current live file is backed up first.

    Returns (ok, result_dict_or_error_string).
    """
    name = clean_name(raw_name)
    if not name:
        return False, 'No robot name given.'

    src = profile_path(name)
    if not os.path.exists(src):
        return False, f'No saved robot called "{name}".'

    ok, err, three_point = check_omd(src)
    if not ok:
        return False, f'"{name}" cannot be loaded: {err}'

    os.makedirs(OHBOT_DATA, exist_ok=True)
    backup = backup_live_file()
    shutil.copy2(src, MOTOR_DEF_FILE)
    set_active(name)

    return True, {
        'name': name,
        'backup': backup,
        'three_point_count': len(three_point),
    }


def delete_profile(raw_name):
    """Remove a saved robot from the library. The live file is untouched."""
    name = clean_name(raw_name)
    if not name:
        return False, 'No robot name given.'
    path = profile_path(name)
    if not os.path.exists(path):
        return False, f'No saved robot called "{name}".'

    # Never actually destroy calibration data — rename it out of the way.
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    shutil.move(path, os.path.join(ROBOTS_DIR, f'{name}.{stamp}.omd.bak'))

    if get_active() == name:
        set_active('')
    return True, {'name': name}


def summary():
    """Everything a web page needs to draw the robot picker."""
    return {
        'robots': list_robots(),
        'active': get_active(),
        'live_file_exists': os.path.exists(MOTOR_DEF_FILE),
    }
