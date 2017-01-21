#!/usr/bin/env python
#
# git-find-lfs-extensions.py [size threshold in KB]
#
# Identify file extensions in a directory tree that could be tracked
# by GitLFS in a repository migration to Git.
#
# Columns explanation:
#   Type      = "binary" or "text".
#   Extension = File extension.
#   LShare    = Percentage of files with the extensions are larger then
#               the threshold.
#   LCount    = Number of files with the extensions are larger then the
#               threshold.
#   Count     = Number of files with the extension in total.
#   Size      = Size of all files with the extension in MB.
#   Min       = Size of the smallest file with the extension in MB.
#   Max       = Size of the largest file with the extension in MB.
#
# Attention this script does only process a directory tree or Git HEAD
# revision. Git history is not taken into account.
#
# Author: Lars Schneider, http://larsxschneider.github.io/
#
import os
import sys

# Threshold that defines a large file
if len(sys.argv):
    THRESHOLD_IN_MB = float(sys.argv[1]) / 1024
else:
    THRESHOLD_IN_MB = 0.5

CWD = os.getcwd()
CHUNKSIZE = 1024
MAX_TYPE_LEN = len("Type")
MAX_EXT_LEN = len("Extension")
result = {}

def is_binary(filename):
    """Return true if the given filename is binary.
    @raise EnvironmentError: if the file does not exist or cannot be accessed.
    @attention: found @ http://bytes.com/topic/python/answers/21222-determine-file-type-binary-text on 6/08/2010
    @author: Trent Mick <TrentM@ActiveState.com>
    @author: Jorge Orpinel <jorge@orpinel.com>"""
    fin = open(filename, 'rb')
    try:
        while 1:
            chunk = fin.read(CHUNKSIZE)
            if b'\0' in chunk: # found null byte
                return True
            if len(chunk) < CHUNKSIZE:
                break # done
    finally:
        fin.close()
    return False

def add_file(ext, type, size_mb):
    global MAX_EXT_LEN
    MAX_EXT_LEN = max(MAX_EXT_LEN, len(ext))
    global MAX_TYPE_LEN
    MAX_TYPE_LEN = max(MAX_TYPE_LEN, len(type))
    if ext not in result:
        result[ext] = {
            'ext' : ext,
            'type' : type,
            'count_large' : 0,
            'size_large' : 0,
            'count_all' : 0,
            'size_all' : 0
        }
    result[ext]['count_all'] = result[ext]['count_all'] + 1
    result[ext]['size_all'] = result[ext]['size_all'] + size_mb
    if size_mb > THRESHOLD_IN_MB:
        result[ext]['count_large'] = result[ext]['count_large'] + 1
        result[ext]['size_large'] = result[ext]['size_large'] + size_mb
    if not 'max' in result[ext] or size_mb > result[ext]['max']:
        result[ext]['max'] = size_mb
    if not 'min' in result[ext] or size_mb < result[ext]['min']:
        result[ext]['min'] = size_mb

def print_line(type, ext, share_large, count_large, count_all, size_all, min, max):
    print('{}{}{}{}{}{}{}{}'.format(
        type.ljust(3+MAX_TYPE_LEN),
        ext.ljust(3+MAX_EXT_LEN),
        str(share_large).rjust(10),
        str(count_large).rjust(10),
        str(count_all).rjust(10),
        str(size_all).rjust(10),
        str(min).rjust(10),
        str(max).rjust(10)
    ))

for root, dirs, files in os.walk(CWD):
    for basename in files:
        filename = os.path.join(root, basename)
        try:
            size_mb = float(os.path.getsize(filename)) / 1024 / 1024
            if not filename.startswith(os.path.join(CWD, '.git')) and size_mb > 0:
                if is_binary(filename):
                    file_type = "binary"
                else:
                    file_type = "text"
                ext = filename
                add_file('*', 'all', size_mb)
                while ext.find('.') >= 0:
                    ext = ext[ext.find('.')+1:]
                    if ext.find('.') <= 0:
                        add_file(ext, file_type, size_mb)
        except Exception as e:
            print(e)

print('')
print_line('Type', 'Extension', 'LShare', 'LCount', 'Count', 'Size', 'Min', 'Max')
print_line('-------', '---------', '-------', '-------', '-------', '-------', '-------', '-------')

for ext in sorted(result, key=lambda x: (result[x]['type'], -result[x]['size_large'])):
    if result[ext]['count_large'] > 0:
        large_share = 100*result[ext]['count_large']/result[ext]['count_all']
        print_line(
            result[ext]['type'],
            ext,
            str(round(large_share)) + ' %',
            result[ext]['count_large'],
            result[ext]['count_all'],
            int(result[ext]['size_all']),
            int(result[ext]['min']),
            int(result[ext]['max'])
        )

print("\nAdd to .gitattributes:\n")
for ext in sorted(result, key=lambda x: (result[x]['type'], x)):
    if len(ext) > 0 and result[ext]['type'] == "binary" and result[ext]['count_large'] > 0:
        print('*.{} filter=lfs diff=lfs merge=lfs -text'.format(
            "".join(c if ('0' <= c <= '9') else "[" + c.upper() + c.lower() + "]" for c in ext)
        ))
