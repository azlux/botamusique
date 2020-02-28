import logging
import os

log = logging.getLogger("bot")


def get_size_folder(path):
    global log

    folder_size = 0
    for (path, dirs, files) in os.walk(path):
        for file in files:
            filename = os.path.join(path, file)
            folder_size += os.path.getsize(filename)
    return int(folder_size / (1024 * 1024))


def clear_tmp_folder(path, size):
    global log

    if size == -1:
        return
    elif size == 0:
        for (path, dirs, files) in os.walk(path):
            for file in files:
                filename = os.path.join(path, file)
                os.remove(filename)
    else:
        if get_size_folder(path=path) > size:
            all_files = ""
            for (path, dirs, files) in os.walk(path):
                all_files = [os.path.join(path, file) for file in files]
                all_files.sort(key=lambda x: os.path.getmtime(x))
            size_tp = 0
            for idx, file in enumerate(all_files):
                size_tp += os.path.getsize(file)
                if int(size_tp / (1024 * 1024)) > size:
                    log.info("Cleaning tmp folder")
                    to_remove = all_files[:idx]
                    print(to_remove)
                    for f in to_remove:
                        log.debug("Removing " + f)
                        os.remove(os.path.join(path, f))
                    return
