#!/usr/bin/env python3

# Mac OS Photo Organizer Utility
# Bret Swalberg (theswally@gmail.com)
# December 2022

import argparse
import os
import datetime
import shutil
from pathlib import Path


def process_folder(src_path_root, dest_path_root, verbose, execute):
    files_found = 0
    dirs_created = 0
    image_files_found = 0
    video_files_found = 0
    files_copied = 0
    dupes_found = 0
    dupes_in_other_folders = 0

    dest_file_dict = build_file_dictionary(dest_path_root, verbose)
    print("--- Transferring Files ----------")

    # Walk through all files and folders recursively in src_path
    #  Move to destination if not already present
    for (dirpath, dirnames, filenames) in os.walk(src_path_root):
        if verbose:
            print("  Path:", dirpath)
            if dirnames:
                print("  Directories:", dirnames)
            if len(filenames):
                print("  - Num Files:", len(filenames))

        # for each folder, loop through all files, and if it's an image/video file process it
        for file in filenames:
            files_found += 1
            if is_image(file) or is_video(file):
                src_path = os.path.join(dirpath, file)
                file_size = os.stat(src_path).st_size
                file_created = os.stat(src_path).st_birthtime
                file_modified = os.stat(src_path).st_mtime
                file_timestamp = file_created   # used in dictionary comparisons with destination

                # there can be discrepancies, so we always opt to take the earliest date between the 2
                if file_created <= file_modified:
                    file_create_ts = datetime.datetime.fromtimestamp(file_created)
                else:
                    file_create_ts = datetime.datetime.fromtimestamp(file_modified)
                    file_timestamp = file_modified

                if is_image(file):
                    image_files_found += 1
                    dest_folder = os.path.join(dest_path_root, get_image_folder(file_create_ts))
                    dest_path = os.path.join(dest_folder, file)
                else:
                    video_files_found += 1
                    dest_folder = os.path.join(dest_path_root, get_video_folder(file_create_ts))
                    dest_path = os.path.join(dest_folder, file)

                if verbose:
                    print("    -File: ", src_path)
                    print("     --Dest Folder:", dest_folder)
                    print("     --Dest Path:", dest_path)

                # see if file already exists at destination.  If yes, then rename in dupe format
                if os.path.isfile(dest_path):
                    dupes_found += 1
                    # print(" **Duplicate found for:", file, "  NO COPY MADE")

                # if not found, check the dictionary to make sure it isn't in a non-standard folder
                elif file in dest_file_dict\
                        and file_timestamp == dest_file_dict[file]['ts']\
                        and file_size == dest_file_dict[file]['size']:
                    dupes_in_other_folders += 1
                    # print(" **Duplicate found in diff location for:", file, "  NO COPY MADE")
                    # print("   -- path:", dest_file_dict[file]['path'])

                # if still not found, copy it
                else:
                    # if destination does not exist, create it first
                    try:
                        if execute:
                            Path(dest_folder).mkdir(parents=True, exist_ok=False)
                            dirs_created += 1
                            print("  ** create new folder:", dest_folder)
                    except FileExistsError:
                        pass
                        # print("Dir exists, no problem:", dest_folder)

                    # copy the file
                    # print ("** copy file from ", src_path, " to ", dest_path)
                    files_copied += 1
                    if execute:
                        shutil.copy2(src_path, dest_path)   # copy2 preserves timestamp metadata

    print("--- Statistics --------")
    print("- Source Files found:", files_found)
    print("  - Image:", image_files_found)
    print("  - Video:", video_files_found)
    print("- Dupes found at dest:", dupes_found+dupes_in_other_folders)
    print("  - Standard folders:", dupes_found)
    print("  - Custom folders:", dupes_in_other_folders)
    print("- Dirs created:", dirs_created)
    print("- Files copied:", files_copied)


# Build a dictionary of all files at path location
# This will allow us to search for duplicates in customer folders, like vacation named folders
def build_file_dictionary(path, verbose_mode):
    print("--- DICTIONARY ----------")
    my_dict = {}
    files_found = 0
    for (dirpath, dirnames, filenames) in os.walk(path):
        if verbose_mode:
            print("  Path:", dirpath)
            if dirnames:
                print("  - Directories:", dirnames)
            if len(filenames):
                print("  - Num Files:", len(filenames))

        for file in filenames:
            if is_image(file) or is_video(file):
                files_found += 1
                src_path = os.path.join(dirpath, file)
                file_created = os.stat(src_path).st_birthtime
                file_modified = os.stat(src_path).st_mtime
                file_timestamp = file_created
                if file_created > file_modified:
                    file_timestamp = file_modified

                file_data = {"size": os.stat(src_path).st_size, "ts": file_timestamp, "path": src_path}
                my_dict[file] = file_data

    print("  Destination media files indexed:", files_found)
    # print(dest_file_dict)
    return my_dict


# use the file create time to determine destination path, in the form:
#  year/'2 digit month'-'2 digit year'
#  ex: file created = 2017-08-21 07:40:51
#  path: 2017/08-21
def get_image_folder(ts):
    # return str(ts.year) + "/" + str(ts.month).zfill(2) + "-" + str(ts.year)[2:]
    return str(ts.year) + "/" + str(ts.year) + "-" + str(ts.month).zfill(2)


def get_video_folder(ts):
    return "videos/" + str(ts.year)


# use filename extension to determine if valid media file (image or video)
def is_image(filename):
    if filename.lower().endswith(('.jpg', 'jpeg', '.gif', '.png')):
        return True
    return False


# use filename extension to determine if valid media file (image or video)
def is_video(filename):
    if filename.lower().endswith(('.mp3', '.mp4', '.mov', '.avi')):
        return True
    return False


if __name__ == '__main__':
    # Setup a command line arg parser with accepted args
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--source", help="Source folder to find photos in")
    parser.add_argument("-d", "--dest", help="Destination folder to put folders in")
    parser.add_argument("-x", "--execute", action='store_true', help="Execute mode, do real copies")
    parser.add_argument("-v", "--verbose", action='store_true', help="Verbose mode, print debug info")

    # Parse incoming cli arguments
    args = parser.parse_args()
    cmd_line_args = vars(args)
    source = cmd_line_args["source"]
    dest = cmd_line_args["dest"]
    execute = cmd_line_args["execute"]
    verbose = cmd_line_args["verbose"]

    print("--- Input Parameters ----------")
    print("  Source:", source)
    print("  Dest:", dest)
    print("  Verbose:", verbose)
    print("  Execute:", execute)

    if not(source and dest):
        print("You must supply a source (-s) and destination (-d)")
    else:
        process_folder(source, dest, verbose, execute)
