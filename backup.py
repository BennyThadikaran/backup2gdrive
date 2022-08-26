import os
import re
from sys import argv
from json import load, dump
from zipfile import ZipFile, ZIP_BZIP2
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

###############################
###   USER SETTINGS BELOW   ###
###############################

# files and folders to ignore/exclude
ignore = ('bin', 'include', 'lib', 'lib64', 'share',
          'pyvenv.cfg', '__pycache__', '.pytest_cache')

###############################
###    END USER SETTINGS    ###
###############################

basepath = os.path.dirname(os.path.realpath(__file__))
yaml_file= f'{basepath}/settings.yaml'

# Escape special regex characters and join the strings with |
# 'bin|include|pyvenv\.cfg'
pattern = '|'.join(map(re.escape, ignore))

# precompile regex
ignore_re = re.compile(pattern)

ext_stripped = os.path.splitext(argv[1])[0]

json_file_info = ext_stripped + '.json'

archive_path = ext_stripped + '.zip'

files_to_backup = argv[2]

print('Adding files to zip')

with ZipFile(archive_path, mode='w', compression=ZIP_BZIP2, compresslevel=9) as zip:

    with open(files_to_backup) as f:
        while i := os.path.expanduser(f.readline().strip()):
            if not os.path.isdir(i):
                zip.write(i)
                continue

            for root, _, files in os.walk(i):
                for file in files:
                    i = os.path.join(root, file)

                    if ignore_re.search(i) is None:
                        zip.write(i)

print('Files zipped:', archive_path)

if os.path.isfile(json_file_info):
    with open(json_file_info) as f:
        data = load(f)
else:
    data = None


gauth = GoogleAuth(settings_file=yaml_file)
gauth.LocalWebserverAuth()

drive = GoogleDrive(gauth)

if data:
    res = drive.CreateFile({'id': data['id']})
else:
    res = drive.CreateFile()

print('Uploading to Google drive')
res.SetContentFile(archive_path)
res.Upload()

with open(json_file_info, 'w') as f:
    dump(res, f, indent=3)

print('Zip file backed up to Google drive.\nFile details saved to', json_file_info)

