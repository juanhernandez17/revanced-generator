# revanced-generator
PyQt application to generate revanced-cli commands
GUI is devided into 3 parts
- top has a list of all apks in apks folder
  - right click will allow to rename apk file to {title}-{version}.apk
  - double click opens apkmirror search in browser
  - columns
    - name = apk path
    - version = apk version
    - update = most recent version patches work for 'Latest' is default
    - output = location where patched apk will be saved
- bottom left will display the generated command
- bottom right will display patches available for selected apk 
  - blue highlight means patch has options<br/>
  - bright blue highlight means required patch has options
  - double click will allow to edit options and show patch information<br/>
  - red highlight means patch is not compatible with current apk version<br/>
- buttons
  - show command - displays command
  - run command - will show the command then open a window to run command
  - save patches - save selected patches to json file
  - select folder - select where the apks/ folder is
- passing any args to gui will generate and run command for all apks in apks/ without the gui
- view menu
  - patch all - patches all apks in apks/ with gui
  - reload - reload ui
- settings.yaml contains settings that can be changed
> aaptFile: adb\aapt - location of aapt  
apkFolder: apks - folder containing all apks  
apkeditorlink: https://github.com/REAndroid/APKEditor/releases/latest - TODO  
errorFile: error.txt - generic error output file  
javaFile: zulu17\bin\java.exe - location for java.exe  
keystoreFile: revanced\revanced.keystore - TODO  
keystorealias: revanced - TODO  
lastupDate: '2023-10-20 00:00:00' - last time that toolsjsonendpoint checked for cli update  
optionsjsonFile: revanced\options.json - general options file  
outputFolder: output - output folder where patched apks are stored  
revancedCacheFolder: revanced-cache - revanced cache folder TODO  
revancedcliFolder: revanced\revanced-cli - location of the revanced-cli.jar files  
revancedintegrationsFolder: revanced\revanced-integrations - location of the revanced-integrations.apk files  
revancedpatchesFolder: revanced\revanced-patches - location of the revanced-patches.jar and .json files  
toolsjsonFile: revanced\tools.json - local copy of revanced-tools.json  
toolsjsonendpoint: https://releases.revanced.app/tools - most recent tools links 

