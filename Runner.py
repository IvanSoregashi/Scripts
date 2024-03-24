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

# CONSTANTS
GDRIVE = Path.home() / 'My Drive'                                   #Contains: iOSAPP img, rec, andss, andvid, andlogs, 
# PCREC = Path.home() / 'Documents' / 'ShareX' / 'Screenshots'        #Contains: 
DLDIR = Path.home() / 'Downloads'                                   #Contains: iOSAPP Logs .zip,  WebApp Logs .log, .har, FW Logs .txt .tar.gz, DL/Conv video .mp4 
ARTIFACTS = Path.home() / 'Artifacts'                               #ARTIFACT DESTINATION

MOVEMENT = True
NOW = d.today()

# CONFIG
logging.basicConfig(filename=ARTIFACTS / 'Runner.log', level=logging.INFO, format='%(asctime)s  [%(levelname)s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# UTILS:
# RENAME TO SUBJECT_RETURN_FROM_PARAMETER
month_str = lambda d: d.strftime(r'%Y-%m')
unix_time = lambda e: dt.fromtimestamp(int(e)).strftime(r'%H-%M-%S')
unix_date = lambda e: dt.fromtimestamp(int(e)).strftime(r'%Y-%m-%d')
ctime_dff = lambda f: dt.fromtimestamp(f.stat().st_ctime).date().strftime(r'%d')
ctime_tff = lambda f: dt.fromtimestamp(f.stat().st_ctime).time().strftime(r'%H-%M-%S')
cdate_dff = lambda f: dt.fromtimestamp(f.stat().st_ctime).date()
mtime_tff = lambda f: dt.fromtimestamp(f.stat().st_mtime).time().strftime(r'%H-%M-%S')

resolve_u = lambda m: unix_time(m.group(0))

ensure_dir_exists = lambda p: p.mkdir(parents=True, exist_ok=True)
path_with_year = lambda p: p.parent / p.name[:4] / p.name
file_exists = lambda f, n: (f.parent / f'{n}{f.suffix}').exists() or (ARTIFACTS / f'{n}{f.suffix}').exists()

files = lambda dir: filter(lambda f: not f.is_dir(), dir.iterdir())
dirs = lambda dir: filter(lambda f: f.is_dir(), dir.iterdir())
month_dirs = lambda dir: filter(lambda d: re.fullmatch(r'^\d\d\d\d-\d\d$', d.name), dir)
year_dirs = lambda dir: filter(lambda d: re.fullmatch(r'^\d\d\d\d$', d.name), dir)
ignore_marked = lambda dir: filter(lambda f: '[x]' not in f.stem, dir)
renamed_files = lambda dir: filter(lambda f: re.match(r'\[[A-Za-z]{3}\] [A-Z]{2}', f.stem), dir)


#DERIVATIVE:
THIS_MONTH = month_str(NOW)
PREV_MONTH = month_str(d(NOW.year, NOW.month, 1) - td(days=2))

# ARTIFACT CLASS
class Artifact:
    def __init__(self, pattern, replace):
        self.pattern = pattern
        self.replace = replace
        self.named = rf'^{replace[:8]}'

    def identify(self, file: Path) -> bool:
        pattern = re.fullmatch(self.pattern, file.stem, re.I)
        if pattern: logging.debug(f'File {file.name} is identified as {self.named[1:]}')
        else: logging.warning(f'File {file.name} is NOT identified as {self.named[1:]}')
        return bool(pattern)

    def new_name(self, file: Path):
        name = re.sub(self.pattern, self.replace, file.stem)
        name = re.sub(r'[0-9]{10,13}', resolve_u, name)
        name = re.sub(r'T\((\d\d)[ .]?(\d\d)[ .]?(\d\d)\)', r'T(\1-\2-\3)', name)
        name = re.sub(r'T\(\)', f'T({ctime_tff(file)})', name)
        name = re.sub(r' T\(', f' {ctime_dff(file)}T(', name)
        name = name.strip(' -')
        while file_exists(file, name): name += '.'
        logging.debug(f'New name is {name}')
        return name

    def rename(self, file: Path, check=False, move=False):
        if not check or self.identify(file):
            logging.info(f'Renaming {file}')
            new_name = self.new_name(file)
            new_path = (ARTIFACTS if move else file.parent) / f'{new_name}{file.suffix}'
            logging.info(f'Ranamed  {new_path}')
            file = file.rename(new_path)
        return file
        
#ARTIFACT OBJECTS
iPad_SS = Artifact(r'^Screenshot (?P<Date>[0-9-]{10}) at (?P<Time>[0-9\.]{8}).*$|^IMG_\d{4}$', r'[iPd] SS T(\g<Time>)')
iPad_RC = Artifact(r'^RPReplay_Final(?P<Time>[0-9]{10})$', r'[iPd] RC T(\g<Time>)')
AndR_SS = Artifact(r'^Screenshot_(?P<Date>[0-9-]{10})-(?P<Time>[0-9-]{8})-\d{3}_com.arlo.(?P<Env>gqa|dev|app)$', r'[And] SS T(\g<Time>) \g<Env> Redmi')
AndN_SS = Artifact(r'^Screenshot \([A-Za-z]{3} [0-9, ]{7,8} (?P<Time>[0-9 ]{8})\)$', r'[And] SS T(\g<Time>) Nothing')
AndR_RC = Artifact(r'^Screenrecorder-(?P<Date>[0-9-]{10})-(?P<Time>[0-9-]{8})-\d{3}$', r'[And] RC T(\g<Time>) Redmi')
AndN_RC = Artifact(r'^screen-(?P<Date>[0-9]{8})-(?P<Time>[0-9]{6})$', r'[And] RC T(\g<Time>) Nothing')
And_LG1 = Artifact(r'^(?P<Name>.*)$', r'[And] LG T() \g<Name>')
And_LG2 = Artifact(r'^Logcat file From Android Device(?P<Info>.*)$', r'[And] LG T() \g<Info>.zip')

iPad_LG = Artifact(r'^(?P<Info>.*)(?P<Date>[0-9-]{10}) (?P<Time>[0-9]{6})$', r'[iPd] LG T(\g<Time>) \g<Info>')
Web_HAR = Artifact(r'^(?P<Info>.*)my(?P<Env>[a-z]+)?\.arlo\.com$', r'[Web] HR T() \g<Env> \g<Info>')
Web_LOG = Artifact(r'^(?P<Info>.*)my(?P<Env>[a-z]+)?\.arlo\.com-(?P<Time>[0-9]{13})$', r'[Web] LG T() \g<Env> \g<Info>')

Web_SSH = Artifact(r'^(?P<App>[A-Za-z0-9]+)_[a-zA-Z0-9]{10}$', r'[Web] SS T() \g<App>')
Web_REC = Artifact(r'^(?P<App>[A-Za-z0-9]+)_[a-zA-Z0-9]{10}$', r'[Web] RC T() \g<App>')

Web_UNI = Artifact(r'^(?P<UN>.*)$', r'[Web] UN T() \g<UN>')


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
    logging.info(f'Moving all files from {dir1.name} to {dir2}')
    for file in (dir1.iterdir() if isinstance(dir1, Path) else dir1):
        logging.debug(f'Moving {file.name}')    
        file.rename(dir2 / file.name)

def artifact_collection_drive():
    logging.info('Starting scan of the Google Drive Folder')
    for file in ignore_marked(files(GDRIVE)):
        match file.suffix.lower():
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
        match file.suffix.lower():
            case '.zip': file = check_for(file, iPad_LG)
            case '.har': file = check_for(file, Web_HAR)
            case '.log': file = check_for(file, Web_LOG)
            case _: ...

def artifact_collection_sharex():
    logging.info('Starting scan of the ShareX subfolders')
    for directory in month_dirs(dirs(ARTIFACTS)):
        for file in ignore_marked(files(directory)):
            match file.suffix.lower():
                case '.png': file = check_for(file, Web_SSH)
                case '.mp4': file = check_for(file, Web_REC)

def return_renamed_files():
    logging.info('Engaging debug fuction of collecting all the files from fubfolders back to the root')
    for directory in month_dirs(dirs(ARTIFACTS)):
        for file in renamed_files(files(directory)):
            logging.debug(f'Moving {file.name} from subfolder {directory.name} to the Artifacts root')
            file.rename(ARTIFACTS / file.name)

def older_to_monthly_subfolders():
    logging.info('Starting the scan of files in the Artifact folder, older files will be moved to the subfolders')
    for file in files(ARTIFACTS):
        if file == 'Runner.log': continue
        date = cdate_dff(file)
        if (NOW - date).days > 5:
            month = month_str(date)
            ensure_dir_exists(ARTIFACTS / month)
            logging.info(f'Moving {file.name} to folder {month}')
            file.rename(ARTIFACTS / month / file.name)

def older_to_yearly_subfolders():
    logging.info('Starting the scan of folders in the Artifact folder, all but two latest will be moved to the yearly folders')
    for directory in month_dirs(dirs(ARTIFACTS)):
        if directory.name in (THIS_MONTH, PREV_MONTH): continue
        move_files(directory, path_with_year(directory))
        directory.rmdir()

def return_monthly_subfolders():
    logging.info('Engaging debug fuction of collecting all monthly subfolders back to the root')
    for directory in year_dirs(dirs(ARTIFACTS)):
        for subfolder in month_dirs(dirs(directory)):
            move_files(subfolder, ARTIFACTS / subfolder.name)
            subfolder.rmdir()

def main():
    logging.info('Starting the Script')
    logging.info('Files will be moved to the Artifact folder' if MOVEMENT else 'Files will be renamed in place')

    artifact_collection_drive()
    artifact_collection_download()
    artifact_collection_sharex()
    #older_to_monthly_subfolders()
    #older_to_yearly_subfolders()
    
    # INSTRUMENTAL FUNCTIONS - RETURN ALL RENAMED FILES TO THE ROOT
    #return_monthly_subfolders()
    #return_renamed_files()

    # ADD - ARCHIVING OLD HARS, RESIZING OLD PICS

    # ADD - ARCHIVING OLD YEARS


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


