#!/usr/bin/env python3

import time
import subprocess
import os
import sys
import shutil as copy
import configparser
import requests
import json
import argparse

config = configparser.ConfigParser()
config.read('ci_build.cfg')
tele_notifier = config['TELE_NOTIFIER']
compiler_cfg = config['COMPILER_CFG']
build_cfg = config['BUILD_CFG']
flashable_cfg = config['FLASHABLE_CFG']

GENERAL_CONFIG = {"TELETOKEN":tele_notifier['TOKEN'], "COMPILER":compiler_cfg['COMPILER'], 
                "CC":compiler_cfg['CC'], "SOURCE_DIR":build_cfg['SOURCE_DIR'], "DEFCONFIG":build_cfg['DEFCONFIG'],
                "CPU":build_cfg['CPU'], "KREL":build_cfg['KREL'], "KBUILD_BUILD_USER":build_cfg['KBUILD_BUILD_USER'], "KBUILD_BUILD_HOST":build_cfg['KBUILD_BUILD_HOST'],
                "KLIB":build_cfg['KLIB'], "FLASHABLE":flashable_cfg['FLASHABLE'], "ZIPNAME":flashable_cfg['ZIPNAME'], "ANYKERNEL_DIR":flashable_cfg['ANYKERNEL_DIR'],
                "DO_DEVICE":flashable_cfg['DO_DEVICE'], "KERNEL_STRING":flashable_cfg['KERNEL_STRING'], "DO_MODULES":flashable_cfg['DO_MODULES'],
                "SUPPORTED_VER":flashable_cfg['SUPPORTED_VER']
}

ENV_CONFIG = {"PATH":compiler_cfg['PATH']+":"+os.environ['PATH'], "CROSS_COMPILE":compiler_cfg['CROSS_COMPILE'], 
              "CROSS_COMPILE_ARM32":compiler_cfg['CROSS_COMPILE_ARM32'], "CLANG_TRIPLE":compiler_cfg['CLANG_TRIPLE'], "CC":compiler_cfg['CC'], "ARCH":build_cfg['ARCH'],
              "KBUILD_BUILD_USER":build_cfg['KBUILD_BUILD_USER'], "KBUILD_BUILD_HOST":build_cfg['KBUILD_BUILD_HOST']
}
for i in ENV_CONFIG:
    os.environ[i] = ENV_CONFIG[i]

elaptime = 0
class TeleNotifier:
    def __init__(self):
        url = "https://api.telegram.org/bot"+GENERAL_CONFIG['TELETOKEN']+"/getUpdates"
        resp = requests.post(url).content
        self.data = json.loads(resp)
        self.latest_id = len(self.data['result']) - 1
        self.chat_id = self.data['result'][self.latest_id]['message']['chat']['id']

    def GetMessage(self):
        message = self.data['result'][self.latest_id]['message']['text']
        return message

    def SendMessage(self, message):
        url = "https://api.telegram.org/bot"+GENERAL_CONFIG['TELETOKEN']+"/sendMessage"
        data = {'chat_id': self.chat_id, 'parse_mode': 'html', 'text': message}
        resp = requests.post(url, data=data)

    def SendFile(self, file):
        url = "https://api.telegram.org/bot"+GENERAL_CONFIG['TELETOKEN']+"/sendDocument"
        data = {'chat_id': self.chat_id}
        resp = requests.post(url, data=data, files={'document': file}).json()

    def SetEnviron(self):
        global GENERAL_CONFIG
        global ENV_CONFIG
        cfg = eval(str(self.data['result'][self.latest_id]['message']['text'].split()).replace("=", "':'").replace("[","{").replace("]", "}").replace("\s",""))
        for i in cfg:
            for j in GENERAL_CONFIG:
                if i == j:
                    GENERAL_CONFIG[j] = cfg[j]
            for l in ENV_CONFIG:
                if i == 'KERNEL_STRING' and l == 'KERNEL_STRING':
                    ENV_CONFIG[l] = cfg[l].replace("<s>", " ")
                    os.environ[l] = ENV_CONFIG[l]
                    continue
                if i == l:
                    ENV_CONFIG[l] = cfg[l]
                    os.environ[l] = cfg[l]

    def elaptimest():
        global elaptime
        elaptime = time.time()

    def elaptimef():       
        h = int(time.time() - elaptime) / 3600
        m = float("0."+str(h).split(".")[1]) * 60
        s = float("0."+str(m).split(".")[1]) * 60
                    
        return int(h), int(m), int(s)

    def status():
        error_detail = ""
        error_count = 0
        warning_count = 0
        for i in open("build.log", "r").readlines():
            if "make" in i:
                i = "" 
            if "warning" in i:
                i = ""  
                warning_count += 1
            if "error:" in i:
                if not error_detail:
                    error_detail += i
                    print(error_detail)
                error_count += 1
        return error_detail, error_count, warning_count

parser = argparse.ArgumentParser()
parser.add_argument("--build", help="Start building kernel", action="store_true")
parser.add_argument("--clean", help="Clean building & log", action="store_true")
parser.add_argument("--verbose", help="Verbosely building process", action="store_true")
parser.add_argument("--tele-notifier", help="Enable telegram bot notifier & fetch configuration", action="store_true")
parser.add_argument("--tele-check", help="Enable build confirmation dialog to telegram bot", action="store_true")
parser.add_argument("--tele-tz", metavar='<Geographic Area/City or Region>', help="Synchrone Telegram Time Zone (e.g: Asia/Jakarta)")
parser.add_argument("--tele-ship", metavar='<File>', help="Ship a file to telegram bot")
args = parser.parse_args()

verbose = False
buf = 0
def build(command, cwd=".", verbose=False):
    global buf
    with open('./build.log', 'a') as log:
        if verbose == True:
            process = subprocess.Popen(command, cwd=cwd, stdout=log, stderr=log, stdin=subprocess.PIPE)
            while True:
                f = open('./build.log', 'r').readlines()
                try:
                    print(f[buf].replace("\n", ""))
                    buf += 1
                except IndexError:
                    if process.poll() is not None:
                        break
        else:
            subprocess.check_call(command, cwd=cwd, stdout=log, stderr=log, stdin=subprocess.PIPE)

def clean():
    build(['make', 'O=../out', 'clean'], cwd=GENERAL_CONFIG['SOURCE_DIR'], verbose=verbose)
    build(['make', 'O=../out', 'mrproper'], cwd=GENERAL_CONFIG['SOURCE_DIR'], verbose=verbose)
    os.system('rm -rf out/* build.log')

def build_image():
    if args.tele_notifier:
        TeleNotifier.elaptimest()
    time.sleep(3)
    try:
        build(['echo', '--------------------', 'BEGIN PREPARE', '--------------------'], verbose=verbose)

        def krel_append(krel):
            buf = open('%s/arch/%s/configs/%s' %(GENERAL_CONFIG['SOURCE_DIR'], ENV_CONFIG['ARCH'], GENERAL_CONFIG['DEFCONFIG']), 'r').readlines()
            count = 0
            for i in buf:
                if "CONFIG_LOCALVERSION" in i:
                    buf[count] = krel
                    wbuf = open('%s/arch/%s/configs/%s' %(GENERAL_CONFIG['SOURCE_DIR'], ENV_CONFIG['ARCH'], GENERAL_CONFIG['DEFCONFIG']), 'w+')
                    wbuf.writelines(buf)
                    wbuf.close()
                    return i 
                count += 1

        if GENERAL_CONFIG['COMPILER'] == "clang" and ENV_CONFIG['CLANG_TRIPLE'] and ENV_CONFIG['CC']:
            if len(GENERAL_CONFIG['KREL']) > 2:
                krel_default = krel_append('CONFIG_LOCALVERSION="%s"' %GENERAL_CONFIG['KREL'])
            build(['make', 'CC=%s' %ENV_CONFIG['CC'], 'O=../out', '%s' %GENERAL_CONFIG['DEFCONFIG']], cwd=GENERAL_CONFIG['SOURCE_DIR'], verbose=verbose)
            build(['echo', '---------------------', 'END PREPARE', '---------------------'], verbose=verbose)
            build(['echo', '\n-------------------', 'BEGIN COMPILING', '-------------------'], verbose=verbose)
            build(['make', 'CC=%s' %ENV_CONFIG['CC'], 'O=../out', '-j%s' %GENERAL_CONFIG['CPU']], cwd=GENERAL_CONFIG['SOURCE_DIR'], verbose=verbose)
            build(['echo', '--------------------', 'END COMPILING', '--------------------'], verbose=verbose)
            if len(GENERAL_CONFIG['KREL']) > 2:
                krel_append(krel_default)
        else:
            if len(GENERAL_CONFIG['KREL']) > 2:
                krel_default = krel_append('CONFIG_LOCALVERSION="%s"' %GENERAL_CONFIG['KREL'])
            build(['make', 'O=../out', '%s' %GENERAL_CONFIG['DEFCONFIG']], cwd=GENERAL_CONFIG['SOURCE_DIR'], verbose=verbose)
            build(['echo', '---------------------', 'END PREPARE', '---------------------'], verbose=verbose)
            build(['echo', '\n-------------------', 'BEGIN COMPILING', '-------------------'], verbose=verbose)
            build(['make', 'O=../out', '-j%s' %GENERAL_CONFIG['CPU']], cwd=GENERAL_CONFIG['SOURCE_DIR'], verbose=verbose) 
            build(['echo', '--------------------', 'END COMPILING', '--------------------'], verbose=verbose)
            if len(GENERAL_CONFIG['KREL']) > 2:
                krel_append(krel_default)
        if os.path.exists("./out/arch/arm64/boot/Image.gz-dtb"):
            if GENERAL_CONFIG['FLASHABLE'] == "False":
                copy.copy2("./out/arch/arm64/boot/Image.gz-dtb", ".")
                if args.tele_notifier:
                    elapsed_time = TeleNotifier.elaptimef()
                    status = TeleNotifier.status()
                    TeleNotifier().SendMessage('<b>[ * ] BUILDING FINISHED!</b>\nat <b>{}</b>\n<b>Elapsed Time</b> : {} h {} min {} sec\n<b>Warning : {}</b>\n<b>Errors</b> : {}\n\n-- CircleCI script by zexceed12300'.format(subprocess.run(['date'], stdout=subprocess.PIPE).stdout.decode("utf-8"), elapsed_time[0], elapsed_time[1], elapsed_time[2], status[2], status[1]))
                    TeleNotifier().SendFile(open("build.log", "rb"))
                    TeleNotifier().SendFile(open("Image.gz-dtb", "rb"))
        else:
            if len(GENERAL_CONFIG['KREL']) > 2:
                    krel_append(krel_default)
            if args.tele_notifier:
                elapsed_time = TeleNotifier.elaptimef()
                status = TeleNotifier.status()
                TeleNotifier().SendMessage('<b>[ ! ] BUILDING FAILED!</b>\nat <b>{}</b>\n<b>Error Preview: </b>\n{}.  .  .\n\n<b>Elapsed Time</b> : {} h {} min {} sec\n<b>Warnings : {}</b>\n<b>Errors</b> : {}\n\n-- CircleCI script by zexceed12300'.format(subprocess.run(['date'], stdout=subprocess.PIPE).stdout.decode("utf-8"), status[0], elapsed_time[0], elapsed_time[1], elapsed_time[2], status[2], status[1]))
                TeleNotifier().SendFile(open("build.log", "rb"))
    except KeyboardInterrupt:
        if len(GENERAL_CONFIG['KREL']) > 2:
                krel_append(krel_default)
        sys.exit()

def build_klib():
    try:
        build(['echo', '\n------------------', 'BEGIN BUILD_KLIB', '-------------------'], verbose=verbose)
        build(['make', 'O=../out', 'modules_install', 'INSTALL_MOD_PATH=../'], cwd=GENERAL_CONFIG['SOURCE_DIR'], verbose=verbose)
        build(['echo', '-------------------', 'END BUILD_KLIB', '--------------------'], verbose=verbose)
    except subprocess.CalledProcessError:
        if args.tele_notifier:
            elapsed_time = TeleNotifier.elaptimef()
            status = TeleNotifier.status()
            TeleNotifier().SendMessage('<b>[ ! ] BUILDING FAILED!</b>\nat <b>{}</b>\n<b>Error Preview: </b>\nFailed to build klib\n.  .  .\n\n<b>Elapsed Time</b> : {} h {} min {} sec\n<b>Warnings : {}</b>\n<b>Errors</b> : {}\n\n-- CircleCI script by zexceed12300'.format(subprocess.run(['date'], stdout=subprocess.PIPE).stdout.decode("utf-8"), elapsed_time[0], elapsed_time[1], elapsed_time[2], status[2], status[1]))
            TeleNotifier().SendFile(open("build.log", "rb"))

def create_zip():
    if os.path.exists("./out/arch/arm64/boot/Image.gz"):
        copy.copy2("./out/arch/arm64/boot/Image.gz-dtb", "%s/" %GENERAL_CONFIG['ANYKERNEL_DIR'])
        buf = open("%s/anykernel.sh" %GENERAL_CONFIG['ANYKERNEL_DIR'], "r").readlines()
        count = 0
        for i in buf:
            if 'kernel.string' in i:
                buf[count] = 'kernel.string=%s\n' %GENERAL_CONFIG['KERNEL_STRING']
            if GENERAL_CONFIG['KLIB'] == "True":
                if 'do.modules' in i:
                    buf[count] = 'do.modules=1\n'
            if 'device.name1' in i:
                buf[count] = 'device.name1=%s\n' %GENERAL_CONFIG['DO_DEVICE']
            if 'supported.version' in i:
                buf[count] = 'supported.version=%s\n' %GENERAL_CONFIG['SUPPORTED_VER']
            count += 1
        wbuf = open("%s/anykernel.sh" %GENERAL_CONFIG['ANYKERNEL_DIR'], "w+")
        wbuf.writelines(buf)
        wbuf.close()
        dirs = []
        if GENERAL_CONFIG['KLIB'] == "True":
            for i in os.walk("./lib/modules"):
                for j in i:
                    dirs.append(j)
                    break
            os.unlink("%s/source" %dirs[1])
            os.unlink("%s/build" %dirs[1])
            try:
                copy.copytree(dirs[1], "%s/modules/system/%s" %(GENERAL_CONFIG['ANYKERNEL_DIR'], dirs[1]))
            except FileExistsError:
                pass
        try:
            build(['echo', '\n----------------', 'BEGIN BUILD_FLASHABLE', '----------------'], verbose=verbose)
            build(["rm", "-rf", ".git/"], cwd=GENERAL_CONFIG['ANYKERNEL_DIR'], verbose=verbose)
            build(['zip', '-r9', '%s.zip' %GENERAL_CONFIG['ZIPNAME'], '.', '-x', 'LICENSE', 'README.md'], cwd=GENERAL_CONFIG['ANYKERNEL_DIR'], verbose=verbose)
            build(['echo', '---------------', 'END BUILD_FLASHABLE', '---------------'], verbose=verbose)
            if os.path.exists("%s/%s.zip" %(GENERAL_CONFIG['ANYKERNEL_DIR'], GENERAL_CONFIG['ZIPNAME'])):
                copy.copy2("%s/%s.zip" %(GENERAL_CONFIG['ANYKERNEL_DIR'], GENERAL_CONFIG['ZIPNAME']), ".")
                if args.tele_notifier:
                    elapsed_time = TeleNotifier.elaptimef()
                    status = TeleNotifier.status()
                    TeleNotifier().SendMessage('<b>[ * ] BUILDING FINISHED!</b>\nat <b>{}</b>\n<b>Elapsed Time</b> : {} h {} min {} sec\n<b>Warnings : {}</b>\n<b>Errors</b> : {}\n\n-- CircleCI script by zexceed12300'.format(subprocess.run(['date'], stdout=subprocess.PIPE).stdout.decode("utf-8"), elapsed_time[0], elapsed_time[1], elapsed_time[2], status[2], status[1]))
                    TeleNotifier().SendFile(open("build.log", "rb"))
                    TeleNotifier().SendFile(open("%s.zip" %GENERAL_CONFIG['ZIPNAME'], "rb"))
        except subprocess.CalledProcessError:
            if args.tele_notifier:
                elapsed_time = TeleNotifier.elaptimef()
                status = TeleNotifier.status()
                TeleNotifier().SendMessage('<b>[ ! ] BUILDING FAILED!</b>\nat <b>{}</b>\n<b>Error Preview: </b>\nFailed to create flashable zip\n.  .  .\n\n<b>Elapsed Time</b> : {} h {} min {} sec\n<b>Warnings : {}</b>\n<b>Errors</b> : {}\n\n-- CircleCI script by zexceed12300'.format(subprocess.run(['date'], stdout=subprocess.PIPE).stdout.decode("utf-8"), elapsed_time[0], elapsed_time[1], elapsed_time[2], status[2], status[1]))
                TeleNotifier().SendFile(open("build.log", "rb"))

if __name__ == "__main__":
    if args.verbose:
        verbose = True

    if args.tele_ship:
        if args.tele_notifier:
            name = args.tele_ship.split('/')
            size = os.path.getsize(args.tele_ship)
            bytes = "B"
            if size > 1000:
                size = size / 1000
                bytes = "kB"
            if size > 1000:
                size = size / 1000
                bytes = "MB"     
            try:
                sys.stdout.write("Sending {} ({:.1f}{})..  ".format(name[0], size, bytes))
                sys.stdout.flush()
                TeleNotifier().SendFile(open(args.tele_ship, 'rb'))
                sys.stdout.write("OK\n")
            except IndexError:
                sys.stdout.write("Sending {} ({:.1f}{})..  ".format(name[0], size, bytes))
                sys.stdout.flush()
                TeleNotifier().SendFile(open(args.tele_ship, 'rb'))
                sys.stdout.write("OK\n")
        else:
            print("Argument --tele-notifier not given.")
        sys.exit()
    
    if args.clean:
        clean()
        sys.exit()

    if args.build:
        if args.tele_notifier:
            if args.tele_tz:
                try:
                    os.unlink("/etc/localtime")
                    os.symlink("/usr/share/zoneinfo/%s" %args.tele_tz, "/etc/localtime")
                except FileNotFoundError:
                    os.symlink("/usr/share/zoneinfo/%s" %args.tele_tz, "/etc/localtime")
            TeleNotifier().SetEnviron()
            if args.tele_check:
                TeleNotifier().SendMessage('<b>[ ? ] BUILD CONFIRMATION!</b>\nat <b>{}</b>\nDo you want continue build? [Y/N]\n\n-- CircleCI script by zexceed12300'.format(subprocess.run(['date'], stdout=subprocess.PIPE).stdout.decode("utf-8")))
                while True:
                    confirm = TeleNotifier().GetMessage()
                    if confirm == "Y":
                        break
                    elif confirm == "N":
                        TeleNotifier().SendMessage('<b>[ ! ] BUILDING ABORTED!</b>\nat <b>{}</b>\n-- CircleCI script by zexceed12300'.format(subprocess.run(['date'], stdout=subprocess.PIPE).stdout.decode("utf-8")))
                        sys.exit()
                    time.sleep(1)
            TeleNotifier().SendMessage('<b>[ + ] BUILDING STARTED!</b>\nat <b>{}</b>\n<b>Device</b> : {}\n<b>Supported Android</b> : {}\n<b>Kernel Release</b> : {}\n<b>Compiler</b> : {}\n<b>Defconfig</b> : {}\n<b>CPU Jobs</b> : {}\n<b>User</b> : {}\n<b>Host</b> : {}\n\n-- CircleCI script by zexceed12300'.format(subprocess.run(['date'], stdout=subprocess.PIPE).stdout.decode("utf-8") ,GENERAL_CONFIG['DO_DEVICE'], GENERAL_CONFIG['SUPPORTED_VER'], GENERAL_CONFIG['KREL'], GENERAL_CONFIG['COMPILER'], GENERAL_CONFIG['DEFCONFIG'], GENERAL_CONFIG['CPU'], GENERAL_CONFIG['KBUILD_BUILD_USER'], GENERAL_CONFIG['KBUILD_BUILD_HOST']))
        build_image()
        if GENERAL_CONFIG['KLIB'] == "True":
            build_klib()
        if GENERAL_CONFIG['FLASHABLE'] == "True":
            create_zip()
        sys.exit()

    parser.print_help()
