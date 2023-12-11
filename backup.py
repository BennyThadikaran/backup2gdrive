import os
import re
import pathlib
from importlib import util as importUtil
from sys import argv
import json
import zipfile
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

###############################
###   USER SETTINGS BELOW   ###
###############################

# files and folders to ignore/exclude
ignore_dir = ('bin', 'include', 'lib', 'lib64', 'share', '__pycache__',
              '.pytest_cache', 'node_modules', '.git')

ignore_files = ('pyvenv.cfg', )

###############################
###    END USER SETTINGS    ###
###############################


def sizeof_fmt(num):
    # source: https://web.archive.org/web/20111010015624/http://blogmag.net/blog/read/38/Print_human_readable_file_size
    for unit in ("bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"):
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}"
        num /= 1024.0
    return f"{num:.1f}YB"


DIR = pathlib.Path(__file__).parent
SETTINGS_FILE = DIR / 'settings.yaml'
BACKUP_FILE_PATH = pathlib.Path(argv[1])
ARCHIVE_PATH = BACKUP_FILE_PATH.with_suffix('.zip')
META_DATAFILE = BACKUP_FILE_PATH.with_name('meta.json')

has_lzma = importUtil.find_spec('lzma')
compressionMethod = zipfile.ZIP_LZMA if has_lzma else zipfile.ZIP_BZIP2

# Escape special regex characters and join the strings with |
# 'bin|include|pyvenv\.cfg'
pattern = '|'.join(map(re.escape, ignore_dir))

# precompile regex
ignore_re = re.compile(pattern)

backup_lst = BACKUP_FILE_PATH.read_text().strip().split('\n')

meta_key = BACKUP_FILE_PATH.stem

if META_DATAFILE.exists():
    meta = json.loads(META_DATAFILE.read_bytes())
else:
    meta = {meta_key: {}}

print('Adding files to zip')

with zipfile.ZipFile(ARCHIVE_PATH,
                     mode='w',
                     compression=compressionMethod,
                     compresslevel=9) as zip:

    for file in backup_lst:
        file = pathlib.Path(file).expanduser()

        if not file.exists():
            print(f'Path not found: {file}')
            continue

        if file.is_file():
            zip.write(file)
            continue

        for root, _, files in os.walk(file, onerror=print):
            if ignore_re.search(root):
                continue

            for f in files:
                if f in ignore_files:
                    continue

                zip.write(pathlib.Path(root).joinpath(f))

print('Files zipped:', ARCHIVE_PATH)

gauth = GoogleAuth(settings_file=str(SETTINGS_FILE))
gauth.LocalWebserverAuth()

drive = GoogleDrive(gauth)

if 'id' in meta[meta_key]:
    res = drive.CreateFile({'id': meta[meta_key]['id']})
else:
    res = drive.CreateFile({'title': ARCHIVE_PATH.name})

file_size = sizeof_fmt(ARCHIVE_PATH.stat().st_size)

print(f'File Size: {file_size}. Uploading to Google drive')

res.SetContentFile(str(ARCHIVE_PATH))
res.Upload()

meta[meta_key]['id'] = res['id']
meta[meta_key]['modifiedDate'] = res['modifiedDate']

META_DATAFILE.write_text(json.dumps(meta, indent=3))

print(f'Zip file backed to Gdrive.\nFile details saved to {META_DATAFILE}')
