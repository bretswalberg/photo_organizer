#!/usr/bin/env python3

# Mac OS Photo Organizer Utility
# Bret Swalberg
# December 2022

import argparse
import os
import datetime
import time
import shutil
from pathlib import Path


def rename_files(src_path_root, verbose, execute):
    files_found = 0
    files_renamed = 0

    print("--- Begin renames ----------")
    for (dirpath, dirnames, filenames) in os.walk(src_path_root):
        if verbose:
            print("  Path:", dirpath)
            if dirnames:
                print("  Directories:", dirnames)
            if len(filenames):
                print("  - Num Files:", len(filenames))

        for file in filenames:
            if is_image(file) or is_video(file):
                files_found += 1
                src_path = os.path.join(dirpath, file)
                file_created = os.stat(src_path).st_birthtime
                file_modified = os.stat(src_path).st_mtime
                file_timestamp = file_created   # used in dictionary comparisons with destination

                # there can be discrepancies, so we always opt to take the earliest date between the 2
                if file_created > file_modified:
                    file_timestamp = file_modified

                # make sure file hasn't previously been renamed
                ts = datetime.datetime.fromtimestamp(file_timestamp)
                if file[0:4] == str(ts.year):
                    print("    - File:", src_path, " appears to have been renamed previously")
                else:
                    new_file_name = format_ts_for_file(file_timestamp) + "_" + file
                    new_src_path = os.path.join(dirpath, new_file_name)
                    files_renamed += 1

                    if verbose:
                        print("  * Renaming file: ", src_path, "->", new_src_path)
                    if execute:
                        os.rename(src_path, new_src_path)

    print("--- Statistics --------")
    print("- Source Files found:", files_found)
    print("- Files renamed:", files_renamed)


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
                else:
                    video_files_found += 1
                    dest_folder = os.path.join(dest_path_root, get_video_folder(file_create_ts))
                dest_path = os.path.join(dest_folder, file)

                if verbose:
                    print("    -File: ", src_path)
                    print("     --Dest Folder:", dest_folder)
                    print("     --Dest Path:", dest_path)

                # TODO
                # duplicate protection has some issues that need resolvig
                # Derek's camera doesn't name files with a datastamp, it just does DSC_0001.jpg, sequentially
                # However there can be many duplicates created with same name, but different timestamp and/or size
                # If a dupe name is found, but size and/or timestamp is diff, it tries to copy it, but this will
                # overwrite the existing file.  Need to find these cases, and copy with an altered name

                # see if file already exists at destination.  If yes, then rename in dupe format
                if os.path.isfile(dest_path):
                    if verbose:
                        print("     **Duplicate found for:", file, "  NO COPY MADE YET")

                    # Determine if duplicate filename is the same file by comparing size and ts
                    # if it's not the same (only in name), append GUID to file in src and then copy
                    # so that we can avoid this problem in subsequent attempts
                    if file_size != dest_file_dict[file]['size'] or file_timestamp != dest_file_dict[file]['ts']:
                        # rename src file
                        new_file_name = format_ts_for_file(file_timestamp) + "_" + file
                        new_src_path = os.path.join(dirpath, new_file_name)
                        new_dest_path = os.path.join(dest_folder, new_file_name)
                        os.rename(src_path, new_src_path)
                        if verbose:
                            print("       ** Dupe file is different, renamed to:", new_src_path)

                        # copy file
                        files_copied += 1
                        if execute:
                            shutil.copy2(new_src_path, new_dest_path)   # copy2 preserves timestamp metadata
                            if verbose:
                                print("      ** copy file from ", new_src_path, " to ", new_dest_path)
                            # TO DO
                            # Add new file to dictionary
                            file_data = {"size": file_size, "ts": file_timestamp, "path": new_src_path}
                            print("** MANUAL dictionary addition ", new_file_name, ": ", file_data)
                            dest_file_dict[new_file_name] = file_data
                    else:
                        dupes_found += 1
                        if verbose:
                            print("     **Same timestamp and size as src, WILL NOT COPY.")

                # if not found, check the dictionary to make sure it isn't in a non-standard folder
                elif file in dest_file_dict\
                        and file_timestamp == dest_file_dict[file]['ts']\
                        and file_size == dest_file_dict[file]['size']:
                    dupes_in_other_folders += 1
                    print(" **Duplicate found in diff location for:", file, "  NO COPY MADE")
                    print("   -- path:", dest_file_dict[file]['path'])

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
                    if verbose:
                        print ("** copy file from ", src_path, " to ", dest_path)
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
    print("--- Dictionary Creation of Destination Files ----------")
    start = time.time()
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

    end = time.time()
    print("  Destination media files indexed:", files_found)
    duration_secs = round(end - start, 1)
    if duration_secs > 0:
        print("  Indexing duration: ", duration_secs, "sec (", round(files_found/duration_secs), "/ sec)")
    # print(dest_file_dict)
    return my_dict


def format_ts_for_file(ts):
    ts = datetime.datetime.fromtimestamp(ts)
    return str(ts.year) + str(ts.month).zfill(2) + str(ts.day).zfill(2)


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
    if filename.lower().endswith(('.jpg', 'jpeg', '.gif', '.png', 'heic')):
        return True
    return False


# use filename extension to determine if valid media file (image or video)
def is_video(filename):
    if filename.lower().endswith(('.mp3', '.mp4', '.mov', '.avi', '.3gp')):
        return True
    return False


if __name__ == '__main__':
    # Setup a command line arg parser with accepted args
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--source", help="Source folder to find photos in")
    parser.add_argument("-d", "--dest", help="Destination folder to put folders in")
    parser.add_argument("-x", "--execute", action='store_true', help="Execute mode, do real copies")
    parser.add_argument("-v", "--verbose", action='store_true', help="Verbose mode, print debug info")
    parser.add_argument("-r", "--rename_with_ts_prefix", action='store_true',
                        help="Rename -s files with a timestamp prefix")

    # Parse incoming cli arguments
    args = parser.parse_args()
    cmd_line_args = vars(args)
    source = cmd_line_args["source"]
    dest = cmd_line_args["dest"]
    execute = cmd_line_args["execute"]
    verbose = cmd_line_args["verbose"]
    rename = cmd_line_args["rename_with_ts_prefix"]

    print("--- Input Parameters ----------")
    print("  Source:", source)
    print("  Dest:", dest)
    print("  Verbose:", verbose)
    print("  Execute:", execute)
    print("  Rename:", rename)

    if rename and source:
        rename_files(source, verbose, execute)
    elif not(source and dest):
        print("You must supply a source (-s) and destination (-d)")
    else:
        process_folder(source, dest, verbose, execute)
