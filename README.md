# Android Kernel Building Script 
# Integrated with CI/CD And Telegram Bot

```
$ python3 ci_build.py --help
usage: ci_build.py [-h] [--build] [--clean] [--verbose] [--tele-notifier] [--tele-check]
                   [--tele-tz <Geographic Area/City or Region>] [--tele-ship <File>]

optional arguments:
  -h, --help            show this help message and exit
  --build               Start building kernel
  --clean               Clean building & log
  --verbose             Verbosely building process
  --tele-notifier       Enable telegram bot notifier & fetch configuration
  --tele-check          Enable build confirmation dialog to telegram bot
  --tele-tz <Geographic Area/City or Region>
                        Synchrone Telegram Time Zone (e.g: Asia/Jakarta)
  --tele-ship <File>    Ship a file to telegram bot
```
## Command Script Arguments
*NOTE*: before building, you must edit the ci_build.cfg according your needed. (Instructions inside)
- Starting building and verbosely building process in your terminal.
  - ```python3 ci_build.py --build --verbose```
- Add ``--tele-notifier`` Argument to Enable Telegram bot integration.
  - ```python3 ci_build.py --build --tele-notifier --verbose```
  - Enable building confirmation dialog to telegram bot. (reply with message ``Y`` to continue building or ``N`` to abort building)
    - ```python3 ci_build.py --build --tele-notifier --tele-check```
  - Synchronize Host Server(CI/CD) with remote timezone.
    - ```python3 ci_build.py --build --tele-notifier --tele-tz Asia/Jakarta```
  - Send file to telegram bot (this is another feature of our scripts. can be used if you remote your CI/CD Server by SSH and need to send a file to telegram bot)
    - ```python3 ci_build.py --build --tele-notifier --tele-ship ./foo.zip```
- Clean build output.
  - ```python3 ci_build.py --clean```
## Integration With Telegram Bot
*NOTE*: ```--tele-notifier``` Commands Script Argument is needed to enable telegram bot integration 
### Overriding ci_build.cfg by sending configuration messages below to telegram bot. 
```
KLIB=True
FLASHABLE=True
DO_DEVICE=rosy
KERNEL_STRING=EternalX<s>Kernel<s>Stable
SUPPORTED_VER=8-9
ZIPNAME=kernel-name
DEFCONFIG=someone_defconfig
CPU=6
COMPILER=clang
USER=zexceed
HOST=lawliet
```
- *NOTE*:
  - that messages must sended before building is started.
  - space not allowed (except KERNEL_STRING use ```<s>``` for space).
  - sending after/during building will cause the configuration not be replaced.
  - message on telegram bot will be readable for 24 hours. if past 24 hour you need send the message again.
  - if configurations is not in the message. it will be follow default ci_build.cfg.
  - that message case sensitive.

## Integration With CI/CD
### Add Building Commands to your CI/CD Configurations (.yml). 
- Configurations Example for <b>[Drone CI](https://drone.io)</b>:
```
--- 
kind: pipeline
name: EternalX-Pipeline

clone:
  depth: 1

steps: 
  - name: Building
    commands:
      - apt-get -y update && apt-get -y upgrade && apt-get -y install bc build-essential bison flex zip gcc clang libc6 curl libstdc++6 git wget libssl-dev && apt-get -y install p7zip-full python python2 python3 python3-pip tzdata
      - git clone https://github.com/zexceed12300/eternalx_ci -b EternalX-project/android_kernel_xiaomi_rosy-3.18 --depth=1
      - cd eternalx_ci
      - git clone https://github.com/EternalX-project/android_kernel_xiaomi_rosy-3.18.git --depth=1
      - git clone https://github.com/zexceed12300/EternalX-flasher --depth=1
      - git clone https://android.googlesource.com/platform/prebuilts/gcc/linux-x86/aarch64/aarch64-linux-android-4.9 -b ndk-release-r16 --depth=1
      - pip3 install -r requirements.txt  
      - python3 ci_build.py --build --tele-notifier --tele-check --verbose --tele-tz Asia/Jakarta
    image: fadlyas/kernel_dockerfile:latest

trigger:
  branch:
    - lineage-18.1
```
- Configurations Example for <b>[CircleCI](https://circleci.com)</b>:
```
version: 2.1
jobs:
  compile:
   docker:
      - image: ubuntu:20.04
   steps:
      - run:
          no_output_timeout: 50m 
          command: |
           apt-get -y update && apt-get -y upgrade && apt-get -y install bc build-essential bison flex zip gcc clang libc6 curl libstdc++6 git wget libssl-dev && apt-get -y install p7zip-full python python2 python3 python3-pip tzdata
           git clone https://github.com/zexceed12300/eternalx_ci -b EternalX-project/android_kernel_xiaomi_rosy-3.18
           cd eternalx_ci
           git clone https://github.com/zexceed12300/EternalX-flasher
           git clone https://github.com/EternalX-project/android_kernel_xiaomi_rosy-3.18.git
           git clone https://android.googlesource.com/platform/prebuilts/gcc/linux-x86/aarch64/aarch64-linux-android-4.9 -b ndk-release-r16 --depth=1
           pip3 install -r requirements.txt   
           python3 ci_build.py --build --tele-notifier --tele-check --verbose --tele-tz Asia/Jakarta
workflows:
  version: 2.1
  cooking:
    jobs:
      - compile
```
### Start building by push some commit to your repository or start directly on CI/CD pipelines.
