import os, re, logging

from pathlib import Path
from zipfile import ZipFile
from datetime import date as d, datetime as dt, timedelta as td
from PIL import Image

# AIM OF THIS SCRIPT:
# 1 COLLECT ARTIFACTS FROM ACROSS THE SYSTEM, TO A SINGLE FOLDER
# 2 DISTRIBUTE ACROSS SUBFOLDERS AS PER CREATION DATE
# 3 CONVERT SOME IMAGES/VIDEO TO REDUCE TRHE SIZE
# 4 RENAME ARTIFACTS TO THE UNIFORM FORMAT PER PLATFORM AND CREATION TIME

# CONFIG
logging.basicConfig(filename='Runner.log', level=logging.DEBUG, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# CONSTANTS
GDRIVE = Path.home() / 'My Drive'                                   #Contains: iOSAPP img, rec, andss, andvid, andlogs, 
# PCREC = Path.home() / 'Documents' / 'ShareX' / 'Screenshots'        #Contains: 
DLDIR = Path.home() / 'Downloads'                                   #Contains: iOSAPP Logs .zip,  WebApp Logs .log, .har, FW Logs .txt .tar.gz, DL/Conv video .mp4 
ARTIFACTS = Path.home() / 'Artifacts'                               #ARTIFACT DESTINATION

MOVEMENT = True
NOW = d.today()

# UTILS:
# RENAME TO SUBJECT_RETURN_FROM_PARAMETER
month_str = lambda d: d.strftime(r'%Y-%m')
unix_time = lambda e: dt.fromtimestamp(int(e)).strftime(r'%H-%M-%S')
unix_date = lambda e: dt.fromtimestamp(int(e)).strftime(r'%Y-%m-%d')
ctime_dff = lambda f: dt.fromtimestamp(f.stat().st_ctime).date().strftime(r'%d')
ctime_tff = lambda f: dt.fromtimestamp(f.stat().st_ctime).time().strftime(r'%H-%M-%S')
mtime_dff = lambda f: dt.fromtimestamp(f.stat().st_mtime).date()
mtime_tff = lambda f: dt.fromtimestamp(f.stat().st_mtime).time().strftime(r'%H-%M-%S')

resolve_u = lambda m: unix_time(m.group(0))

ensure_dir_exists = lambda p: p.mkdir(parents=True, exist_ok=True)
path_with_year = lambda p: p.parent / p.name[:4] / p.name
file_exists = lambda f, n: (f.parent / f'{n}{f.suffix}').exists() or (ARTIFACTS / f'{n}{f.suffix}').exists()

files = lambda dir: filter(lambda f: not f.is_dir(), dir.iterdir())
dirs = lambda dir: filter(lambda f: f.is_dir(), dir.iterdir())
month_dirs = lambda dir: filter(lambda d: re.fullmatch(r'^\d\d\d\d-\d\d$', d.name), dir)
ignore_marked = lambda dir: filter(lambda f: '[x]' not in f.stem, dir)

#DERIVATIVE:
THIS_MONTH = month_str(NOW)
PREV_MONTH = month_str(d(NOW.year, NOW.month, 1) - td(days=2))

# ARTIFACT CLASS
class Artifact:
    def __init__(self, pattern=None, replace=None, suffix=None):
        if not (pattern or suffix):
            raise Exception('Artifact needs to be identified by either pattrn or suffix')            
        self.pattern = pattern
        self.replace = replace
        self.suffix = suffix
        self.named = rf'^{replace[:8]}'

    def identify(self, file: Path) -> bool:
        logging.debug(f'Identifying the file {file.name} as {self.named}')
        suffix = self.suffix == file.suffix.lower() if self.suffix else True
        pattern = re.fullmatch(self.pattern, file.stem, re.I) if self.pattern else True
        return bool(suffix and pattern)

    def new_name(self, file: Path):
        name = re.sub(self.pattern, self.replace, file.stem)
        name = re.sub(r'[0-9]{10,13}', resolve_u, name)
        name = re.sub(r'T\((\d\d)[ .]?(\d\d)[ .]?(\d\d)\)', r'T(\1-\2-\3)', name)
        name = re.sub(r'T\(\)', f'T({ctime_tff(file)})', name)
        name = re.sub(r' T\(', f' {ctime_dff(file)}T(', name)
        while file_exists(file, name): name += '.'
        logging.debug(f'New name is evaluated to {name}')
        return name

    def rename(self, file: Path, check=False, move=False):
        if not check or self.identify(file):
            new_name = self.new_name(file)
            new_path = (ARTIFACTS if move else file.parent) / f'{new_name}{file.suffix}'
            logging.debug(f'Renaming {file}')
            logging.info(f'New name {new_path}')
            #file = file.rename(new_path)
        return file
        
#ARTIFACT OBJECTS
iPad_SS = Artifact(r'^Screenshot (?P<Date>[0-9-]{10}) at (?P<Time>[0-9\.]{8}).*$|^IMG_\d{4}$', r'[iPd] SS T(\g<Time>)', r'.png')
iPad_RC = Artifact(r'^RPReplay_Final(?P<Time>[0-9]{10})$', r'[iPd] RC T(\g<Time>)', r'.mp4')
#And_SSH = Artifact(r'^Screenshot_(?P<Date>[0-9-]{10})-(?P<Time>[0-9-]{8})-\d{3}_com.arlo.(?P<Env>gqa|dev|app)$|^Screenshot \([A-Za-z]{3} [0-9, ]{7,8} (?P<Time>[0-9 ]{8})\)$', r'[And] SS T(\g<Time>)', r'.jpg')
AndR_SS = Artifact(r'^Screenshot_(?P<Date>[0-9-]{10})-(?P<Time>[0-9-]{8})-\d{3}_com.arlo.(?P<Env>gqa|dev|app)$', r'[And] SS T(\g<Time>) \g<Env> Redmi', r'.jpg')
AndN_SS = Artifact(r'^Screenshot \([A-Za-z]{3} [0-9, ]{7,8} (?P<Time>[0-9 ]{8})\)$', r'[And] SS T(\g<Time>) Nothing', r'.jpg')
#And_REC = Artifact(r'^Screenrecorder-(?P<Date>[0-9-]{10})-(?P<Time>[0-9-]{8})-\d{3}$|^screen-(?P<Date>[0-9]{8})-(?P<Time>[0-9]{6})$', r'[And] RC T(\g<Time>)', r'.mp4')
AndR_RC = Artifact(r'^Screenrecorder-(?P<Date>[0-9-]{10})-(?P<Time>[0-9-]{8})-\d{3}$', r'[And] RC T(\g<Time>) Redmi', r'.mp4')
AndN_RC = Artifact(r'^screen-(?P<Date>[0-9]{8})-(?P<Time>[0-9]{6})$', r'[And] RC T(\g<Time>) Nothing', r'.mp4')
And_LG1 = Artifact(r'^(?P<Name>.*)$', r'[And] LG T() \g<Name>', r'.zip')
And_LG2 = Artifact(r'^Logcat file From Android Device(?P<Info>.*)$', r'[And] LG T() \g<Info>.zip', r'')

iPad_LG = Artifact(r'^(?P<Date>[0-9-]{10}) (?P<Time>[0-9]{6})$', r'[iPd] LG T(\g<Time>)', r'.zip')
Web_HAR = Artifact(r'^(?P<Info>.*)my(?P<Env>[a-z]+)?\.arlo\.com$', r'[Web] HR T() \g<Env> \g<Info>', r'.har')
Web_LOG = Artifact(r'^(?P<Info>.*)my(?P<Env>[a-z]+)?\.arlo\.com-(?P<Time>[0-9]{13})$', r'[Web] LG T() \g<Env> \g<Info>', r'.log')

Web_SSH = Artifact(r'^(?P<App>[A-Za-z0-9]+)_[a-zA-Z0-9]{10}$', r'[Web] SS T() \g<App>', r'.png')
Web_REC = Artifact(r'^(?P<App>[A-Za-z0-9]+)_[a-zA-Z0-9]{10}$', r'[Web] RC T() \g<App>', r'.mp4')


def zip_is_android_logs(file: Path) -> bool:
    with ZipFile(file) as zf:
        return any(map(lambda f: f.filename == 'ArloLogs/', zf.filelist))

def check_for(file, *arts):
    for art in arts:
        file = art.rename(file, check=True, move=MOVEMENT)
    return file

def move_files(dir1, dir2):
    'dir1 - source folder or collection of paths, dir2 - destination folder'
    ensure_dir_exists(dir2)
    logging.info(f'Moving all files from {dir1} to {dir2}')
    for file in (dir1.iterdir() if isinstance(dir1, Path) else dir1):
        logging.debug(f'Moving {file.name}')
        file.rename(dir2 / file.name)

def artifact_collection_drive():
    logging.info('Starting scan of the Google Drive Folder')
    for file in ignore_marked(files(GDRIVE)):
        match file.suffix:
            case '':
                if zip_is_android_logs(file): file = And_LG2.rename(file, move=MOVEMENT)
                else: file = file.rename(file.parent / f'{file.stem}[x]{file.suffix}')
            case '.zip': 
                if zip_is_android_logs(file): file = And_LG1.rename(file, move=MOVEMENT)
                else: file = file.rename(file.parent / f'{file.stem}[x]{file.suffix}')
            case '.png': file = check_for(file, iPad_SS)
            case '.jpg': file = check_for(file, AndN_SS, AndR_SS)
            case '.mp4': file = check_for(file, iPad_RC, AndN_RC, AndR_RC)
            case _: ...

def artifact_collection_download():
    logging.info('Starting scan of the Downloads Folder')
    for file in ignore_marked(files(DLDIR)):
        match file.suffix:
            case '.zip': file = check_for(file, iPad_LG)
            case '.har': file = check_for(file, Web_HAR)
            case '.log': file = check_for(file, Web_LOG)
            case _: ...

def artifact_collection_sharex():
    logging.info('Starting scan of the ShareX subfolders')
    for directory in month_dirs(dirs(ARTIFACTS)):
        for file in ignore_marked(files(directory)):
            match file.suffix:
                case '.png': file = check_for(file, Web_SSH)
                case '.mp4': file = check_for(file, Web_REC)

def group_by_date():
    logging.info('Starting the scan of files in the Artifact folder, older files will be moved to the subfolders')
    for file in files(ARTIFACTS):
        date = ctime_dff(file)
        if (NOW - date).days > 5:
            ensure_dir_exists(ARTIFACTS / month_str(date))
            file.rename(ARTIFACTS / month_str(date) / file.name)
    
    logging.info('Starting the scan of directories in the Artifact folder, all but two latest will be moved to the yearly folders')
    for directory in month_dirs(dirs(ARTIFACTS)):
        if directory.name in (THIS_MONTH, PREV_MONTH): continue
        move_files(directory, path_with_year(directory))
        directory.rmdir()

    # ADD - ARCHIVING OLD HARS, RESIZING OLD PICS

    # ADD - ARCHIVING OLD YEARS

def main():
    # PRINT OUT LOGS
    logging.info('Starting the Script')
    logging.info('Files will be moved to the Artifact folder' if MOVEMENT else 'Files will be renamed in place')

    artifact_collection_drive()
    #artifact_collection_download()
    #artifact_collection_sharex()
    #group_by_date()

if __name__ == '__main__':
    main()

'''
    image = Image.open(file)
    #IPAD IMAGES
    if image.size == (2048, 2732):
        image = image.resize(size=(1024, 1366), resample=Image.Resampling.BICUBIC)
        suffix = 'jpg' if file.suffix == '.jpg' else 'png' if os.path.getsize(file) < 1000000 else 'jpg'
        image.convert(mode="RGB").save(ARTIFACTS / 'resize' / f'{name}.{suffix}')
        #file.unlink()'''


