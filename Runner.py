import os, re

from pathlib import Path
from zipfile import ZipFile
#from abc import ABC, abstractmethod
#from itertools import chain
from datetime import date as d, datetime as dt, timedelta as td
from PIL import Image

# AIM OF THIS SCRIPT:
# 1 COLLECT ARTIFACTS FROM ACROSS THE SYSTEM, TO A SINGLE FOLDER
# 2 DISTRIBUTE ACROSS SUBFOLDERS AS PER CREATION DATE
# 3 CONVERT SOME IMAGES/VIDEO TO REDUCE TRHE SIZE
# 4 RENAME ARTIFACTS TO THE UNIFORM FORMAT PER PLATFORM AND CREATION TIME

#CONSTANTS
GDRIVE = Path.home() / 'My Drive'                                   #Contains: iOSAPP img, rec, andss, andvid, andlogs, 
#PCREC = Path.home() / 'Documents' / 'ShareX' / 'Screenshots'        #Contains: 
DLDIR = Path.home() / 'Downloads'                                   #Contains: iOSAPP Logs .zip,  WebApp Logs .log, .har, FW Logs .txt .tar.gz, DL/Conv video .mp4 
ARTIFACTS = Path.home() / 'Artifacts'                               #ARTIFACT DESTINATION
MOVEMENT = True

#UTILS:
month_str = lambda d: d.strftime(r'%Y-%m')
unix_time = lambda e: dt.fromtimestamp(int(e)).strftime(r'%H-%M-%S')
unix_date = lambda e: dt.fromtimestamp(int(e)).strftime(r'%Y-%m-%d')
resolve_u = lambda m: unix_time(m.group(0))
ctime_dff = lambda f: dt.fromtimestamp(f.stat().st_ctime).date().strftime(r'%d')
ctime_tff = lambda f: dt.fromtimestamp(f.stat().st_ctime).time().strftime(r'%H-%M-%S')
mtime_dff = lambda f: dt.fromtimestamp(f.stat().st_mtime).date()
mtime_tff = lambda f: dt.fromtimestamp(f.stat().st_mtime).time().strftime(r'%H-%M-%S')
ensure_dir_exists = lambda p: p.mkdir(parents=True, exist_ok=True)
file_exists = lambda f, n: (f.parent / f'{n}{f.suffix}').exists() or (ARTIFACTS / f'{n}{f.suffix}').exists()

#DERIVATIVE:
NOW = d.today()
THIS_MONTH = month_str(NOW)
PREV_MONTH = month_str(d(NOW.year, NOW.month, 1) - td(days=2))
PRE2_MONTH = month_str(d(NOW.year, NOW.month, 1) - td(days=33))

class Artifact:
    def __init__(self, pattern=None, sub=None, suffix=None):
        if not (pattern or suffix):
            raise Exception('Artifact needs to be identified by either pattrn or suffix')            
        self.pattern = pattern
        self.sub = sub
        self.suffix = suffix

    def identify(self, file: Path) -> bool:
        suffix = self.suffix == file.suffix.lower() if self.suffix else True
        pattern = re.fullmatch(self.pattern, file.stem, re.I) if self.pattern else True
        return bool(suffix and pattern)

    def new_name(self, file: Path):
        name = re.sub(self.pattern, self.sub, file.stem)
        name = re.sub(r'[0-9]{10,13}', resolve_u, name)
        name = re.sub(r'T\((\d\d)[ .]?(\d\d)[ .]?(\d\d)\)', r'T(\1-\2-\3)', name)
        name = re.sub(r'T\(\)', f'T({ctime_tff(file)})', name)
        name = re.sub(r' T\(', f' {ctime_dff(file)}T(', name)
        while file_exists(file, name): name += '.'
        print(f'{file.name}\t-->\t{name}')
        return name

    def rename(self, file: Path, check=False, move=False):
        if not check or self.identify(file):
            new_name = self.new_name(file)
            #file = file.rename((ARTIFACTS if move else file.parent) / f'{new_name}{file.suffix}')
        return file
        
    
#ARTIFACT OBJECTS
iPad_SS = Artifact(r'^Screenshot (?P<Date>[0-9-]{10}) at (?P<Time>[0-9\.]{8}).*$|^IMG_\d{4}$', r'[iPd] SS T(\g<Time>)', r'.png')
iPad_RC = Artifact(r'^RPReplay_Final(?P<Time>[0-9]{10})$', r'[iPd] RC T(\g<Time>)', r'.mp4')
And_SSH = Artifact(r'^Screenshot_(?P<Date>[0-9-]{10})-(?P<Time>[0-9-]{8})-\d{3}_com.arlo.(?P<Env>gqa|dev|app)$|^Screenshot \([A-Za-z]{3} [0-9, ]{7,8} (?P<Time>[0-9 ]{8})\)$', r'[And] SS T(\g<Time>)', r'.jpg')
AndR_SS = Artifact(r'^Screenshot_(?P<Date>[0-9-]{10})-(?P<Time>[0-9-]{8})-\d{3}_com.arlo.(?P<Env>gqa|dev|app)$', r'[And] SS T(\g<Time>) \g<Env> Redmi', r'.jpg')
AndN_SS = Artifact(r'^Screenshot \([A-Za-z]{3} [0-9, ]{7,8} (?P<Time>[0-9 ]{8})\)$', r'[And] SS T(\g<Time>) Nothing', r'.jpg')
And_REC = Artifact(r'^Screenrecorder-(?P<Date>[0-9-]{10})-(?P<Time>[0-9-]{8})-\d{3}$|^screen-(?P<Date>[0-9]{8})-(?P<Time>[0-9]{6})$', r'[And] RC T(\g<Time>)', r'.mp4')
AndR_RC = Artifact(r'^Screenrecorder-(?P<Date>[0-9-]{10})-(?P<Time>[0-9-]{8})-\d{3}$', r'[And] RC T(\g<Time>) Redmi', r'.mp4')
AndN_RC = Artifact(r'^screen-(?P<Date>[0-9]{8})-(?P<Time>[0-9]{6})$', r'[And] RC T(\g<Time>) Nothing', r'.mp4')
And_LG1 = Artifact(r'^(?P<Name>.*)$', r'[And] LG T() \g<Name>', r'.zip')
And_LG2 = Artifact(r'^Logcat file From Android Device(?P<Info>.*)$', r'[And] LG T() \g<Info>.zip', r'')

iPad_LG = Artifact(r'^(?P<Date>[0-9-]{10}) (?P<Time>[0-9]{6})$', r'[iPd] LG T(\g<Time>)', r'.zip')
Web_HAR = Artifact(r'^(?P<Info>.*)my(?P<Env>[a-z]+)?\.arlo\.com$', r'[Web] HR T() \g<Env> \g<Info>', r'.har')
Web_LOG = Artifact(r'^(?P<Info>.*)my(?P<Env>[a-z]+)?\.arlo\.com-(?P<Time>[0-9]{13})$', r'[Web] LG T() \g<Env> \g<Info>', r'.log')

Web_SSH = Artifact(r'^(?P<App>[a-z0-9]+)_[a-zA-Z0-9]{10}$', r'[Web] SS T() \g<App>', r'.png')
Web_REC = Artifact(r'^(?P<App>[a-z0-9]+)_[a-zA-Z0-9]{10}$', r'[Web] RC T() \g<App>', r'.mp4')


def zip_is_android_logs(file: Path) -> bool:
    with ZipFile(file) as zf:
        return any(map(lambda f: f.filename == 'ArloLogs/', zf.filelist))

def check_for(file, *arts):
    for art in arts:
        file = art.rename(file, check=True, move=MOVEMENT)
    return file

def folder_structure_update():
    # CHECKING THIS MONTHS FOLDER
    ensure_dir_exists(ARTIFACTS / THIS_MONTH)
    
    # MOVING 2 MONTHS OLD FOLDER
    old_path = ARTIFACTS / PRE2_MONTH
    if old_path.exists():
        new_path = ARTIFACTS / PRE2_MONTH[:4] / PRE2_MONTH
        ensure_dir_exists(new_path)
        for file in old_path.iterdir():
            file.rename(new_path / file.name)
        old_path.rmdir()

    # ADD - ARCHIVING OLD HARS, RESIZING OLD PICS

    # ADD - ARCHIVING OLD YEARS

def artifact_collection():
    for file in GDRIVE.iterdir():
        # IGNORE THE DIRECTORIES
        if file.is_dir(): 
            continue
        # IGNORE MARKED
        if '[x]' in file.stem: 
            continue
        # CHECK IF ZIPS ARE ANDROID LOGS, MARK THOSE WHO AREN'T
        if file.suffix == '.zip':
            
            continue
        # CHECKS PATTERNS ONE AFTER ANOTHER
        #for pattern in DRIVE_ARTIFACTS:
        #    if re.fullmatch(pattern, file.stem, re.I):
        #        file = DRIVE_ARTIFACTS[pattern].rename(file)
        # REPLACE THIS WITH LAYERED SEARCH, STARTING WITH SUFFIX, THEN WITH REGEX, WITH FUTURE EXTENSION BY ANALISYNG THE PIC
        '''if file.suffix == '.png':
            iPad_SS.rename(file, check=True, move=MOVEMENT)
        if file.suffix == '.jpg':
            AndN_SS.rename(file, check=True, move=MOVEMENT)
            AndR_SS.rename(file, check=True, move=MOVEMENT)
        if file.suffix == '.mp4':
            iPad_RC.rename(file, check=True, move=MOVEMENT)
            AndN_RC.rename(file, check=True, move=MOVEMENT)
            AndR_RC.rename(file, check=True, move=MOVEMENT)
'''
        match file.suffix:
            case '.zip': 
                if zip_is_android_logs(file): And_LG1.rename(file, move=MOVEMENT)
                else: file.rename(file.parent / f'{file.stem}[x]{file.suffix}')
            case '.png': file = check_for(file, iPad_SS)
            case '.jpg': file = check_for(file, AndN_SS, AndR_SS)
            case '.mp4': file = check_for(file, iPad_RC, AndN_RC, AndR_RC)
            case '': file = check_for(file, And_LG2)
            case _: ...
        '''if file.suffix in ('.jpg','.png'):
            image = Image.open(file)
            #IPAD IMAGES
            print(file.name, image.size, os.path.getsize(file))
            if image.size == (2048, 2732):
                if re.match(ipss_pattern, file.stem):
                    date = re.search(ipss_pattern, file.stem).group(1)
                    time = re.search(ipss_pattern, file.stem).group(2).replace('.', '_')
                    name = f'iPSS {time}'
                else:
                    name = file.stem.split('.')[0].replace('Screenshot ', 'iPSS ')
                
                image = image.resize(size=(1024, 1366), resample=Image.Resampling.BICUBIC)
                suffix = 'jpg' if file.suffix == '.jpg' else 'png' if os.path.getsize(file) < 1000000 else 'jpg'
                image.convert(mode="RGB").save(ARTIFACTS / 'resize' / f'{name}.{suffix}')
                #file.unlink()'''
        

    for file in DLDIR.iterdir():
        if file.suffix in ('.jpg','.png', '.txt', '.zip'):
            ... # print(file.name, ctime_tff(file), os.path.getsize(file))

    #for file in (PCREC / THIS_MONTH).iterdir():
    #    ... # print(file.name, ctime_tff(file), os.path.getsize(file))

    #for file in (PCREC / PREV_MONTH).iterdir():
    #   ... # print(file.name, ctime_tff(file), os.path.getsize(file))

def main():
    folder_structure_update()
    artifact_collection()

if __name__ == '__main__':
    main()




