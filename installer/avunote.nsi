; Avunote per-user installer. Application license does not replace component licenses.
Unicode true
RequestExecutionLevel user
ManifestDPIAware true
ManifestSupportedOS all
SetCompressor /FINAL zlib
SetDatablockOptimize on
SetOverwrite on
CRCCheck force
SetFont "Segoe UI" 9

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"
!include "x64.nsh"
!include "WinVer.nsh"

!ifndef RELEASEDIR
  !error "RELEASEDIR must name the verified model-free binary release directory."
!endif
!ifndef UNINSTALL_INCLUDE
  !error "Generate UNINSTALL_INCLUDE using scripts/build_installer.ps1."
!endif
!ifndef OUTPUT_EXE
  !error "OUTPUT_EXE is required."
!endif
!ifndef SOURCE_ROOT
  !error "SOURCE_ROOT is required."
!endif
!ifndef APP_VERSION
  !define APP_VERSION "2.4.0"
!endif
!ifndef ESTIMATED_KIB
  !define ESTIMATED_KIB 0
!endif

Name "Avunote"
OutFile "${OUTPUT_EXE}"
InstallDir "$LOCALAPPDATA\Programs\Avunote"
; Retain the original installer identity so existing Voxriva installs upgrade
; in place. Visible names, shortcuts and executable use the Avunote brand.
InstallDirRegKey HKCU "Software\Voxriva" "InstallDir"
BrandingText "Avunote"
ShowInstDetails show
ShowUninstDetails show
VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey /LANG=1033 "ProductName" "Avunote"
VIAddVersionKey /LANG=1033 "CompanyName" "Fardin Milani"
VIAddVersionKey /LANG=1033 "FileDescription" "Avunote per-user setup"
VIAddVersionKey /LANG=1033 "FileVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1033 "LegalCopyright" "Fardin Milani; third-party rights retained"

!define MUI_ICON "${SOURCE_ROOT}\assets\avunote.ico"
!define MUI_UNICON "${SOURCE_ROOT}\assets\avunote.ico"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE "Welcome to Avunote"
!define MUI_WELCOMEPAGE_TEXT "Offline transcription with a downloadable model library, plus AI chat and language practice.$\r$\n$\r$\nExisting models, preferences and chats are preserved. Choose which speech models to download in the app after installation.$\r$\n$\r$\nClose Avunote or Voxriva before upgrading."
!insertmacro MUI_PAGE_WELCOME
!define MUI_LICENSEPAGE_TEXT_TOP "Avunote application code is MIT-licensed. Bundled components retain their own terms; see Licenses and THIRD_PARTY_NOTICES.md."
!define MUI_LICENSEPAGE_TEXT_BOTTOM "Click Next to continue. No additional license restrictions are added."
!define MUI_LICENSEPAGE_BUTTON "Next >"
!insertmacro MUI_PAGE_LICENSE "${SOURCE_ROOT}\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_TITLE "Avunote is ready"
!define MUI_FINISHPAGE_TEXT "Avunote has been installed. You can download language models from the app when needed.$\r$\n$\r$\nYour existing models, preferences and private data are preserved."
!define MUI_FINISHPAGE_RUN "$INSTDIR\Avunote.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch Avunote"
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!define MUI_FINISHPAGE_SHOWREADME ""
!define MUI_FINISHPAGE_SHOWREADME_TEXT "Create a desktop shortcut"
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED
!define MUI_FINISHPAGE_SHOWREADME_FUNCTION CreateDesktopShortcut
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH
!insertmacro MUI_LANGUAGE "English"

Var SmokeMode
Var Parameters
Var ExistingInstall
Var DesktopShortcutRequested
Var DirectUpdate
Var FromVersion

!macro EnsureApplicationClosed Exe Label
  IfFileExists "$INSTDIR\${Exe}" 0 ${Label}_closed
${Label}_check:
  System::Call 'kernel32::CreateFileW(w "$INSTDIR\${Exe}", i 0x80000000, i 0, p 0, i 3, i 0, p 0) p.r0'
  ${If} $0 == -1
    MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "Close Avunote or Voxriva before installing or upgrading." /SD IDCANCEL IDRETRY ${Label}_check
    SetErrorLevel 2
    Abort
  ${EndIf}
  System::Call 'kernel32::CloseHandle(p r0)'
${Label}_closed:
!macroend

!macro DefineValidateInstallDir Prefix
Function ${Prefix}ValidateInstallDir
  ClearErrors
  ; Native GetFullPathName accepts a new directory that does not exist yet.
  System::Call 'kernel32::GetFullPathNameW(w "$INSTDIR\.", i ${NSIS_MAX_STRLEN}, w .r0, p 0) i.r2'
  ${If} $2 == 0
  ${OrIf} $2 >= ${NSIS_MAX_STRLEN}
  ${OrIf} $0 == ""
    SetErrors
    Return
  ${EndIf}
  ${GetRoot} "$0" $1
  ${If} $0 == "$1"
  ${OrIf} $0 == "$1\"
  ${OrIf} $0 == "$WINDIR"
  ${OrIf} $0 == "$SYSDIR"
  ${OrIf} $0 == "$PROFILE"
  ${OrIf} $0 == "$DOCUMENTS"
  ${OrIf} $0 == "$DESKTOP"
  ${OrIf} $0 == "$LOCALAPPDATA"
  ${OrIf} $0 == "$APPDATA"
  ${OrIf} $0 == "$TEMP"
  ${OrIf} $0 == "$PROGRAMFILES"
  ${OrIf} $0 == "$PROGRAMFILES64"
    SetErrors
    Return
  ${EndIf}
  StrCpy $INSTDIR "$0"
FunctionEnd
!macroend
!insertmacro DefineValidateInstallDir ""
!insertmacro DefineValidateInstallDir "un."

Function .onInit
  SetShellVarContext current
  StrCpy $SmokeMode "0"
  ${GetParameters} $Parameters
  ClearErrors
  ${GetOptions} "$Parameters" "/TESTMODE" $0
  ${IfNot} ${Errors}
    StrCpy $SmokeMode "1"
  ${EndIf}
  ${IfNot} ${RunningX64}
    MessageBox MB_OK|MB_ICONSTOP "Avunote requires 64-bit Windows 10 or Windows 11." /SD IDOK
    SetErrorLevel 2
    Quit
  ${EndIf}
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_OK|MB_ICONSTOP "Avunote requires Windows 10 or Windows 11." /SD IDOK
    SetErrorLevel 2
    Quit
  ${EndIf}
  SetRegView 64
  StrCpy $DirectUpdate "0"
  ClearErrors
  ${GetOptions} "$Parameters" "/AVUNOTEUPDATE" $0
  ${IfNot} ${Errors}
    StrCpy $DirectUpdate "1"
    ClearErrors
    ${GetOptions} "$Parameters" "/FROMVERSION=" $FromVersion
    ${If} ${Errors}
      SetErrorLevel 2
      Quit
    ${EndIf}
    ClearErrors
    ${GetOptions} "$Parameters" "/WAITPID=" $0
    ${IfNot} ${Errors}
      ; Wait for the app's own close handler to finish, including its worker shutdown.
      System::Call 'kernel32::OpenProcess(i 0x00100000, i 0, i r0) p.r1'
      ${If} $1 != 0
        System::Call 'kernel32::WaitForSingleObject(p r1, i 45000) i.r2'
        System::Call 'kernel32::CloseHandle(p r1)'
        ${If} $2 != 0
          MessageBox MB_OK|MB_ICONSTOP "Avunote could not close. Start the app and try the update again."
          SetErrorLevel 2
          Quit
        ${EndIf}
      ${EndIf}
    ${EndIf}
  ${EndIf}
FunctionEnd

Function .onVerifyInstDir
  Call ValidateInstallDir
  ${If} ${Errors}
    Abort
  ${EndIf}
FunctionEnd

Function CreateDesktopShortcut
  ${If} $SmokeMode != "1"
    CreateShortcut "$DESKTOP\Avunote.lnk" "$INSTDIR\Avunote.exe" "" "$INSTDIR\Avunote.exe" 0
    WriteINIStr "$INSTDIR\.voxriva-install.ini" "Voxriva" "DesktopShortcut" "1"
  ${EndIf}
FunctionEnd

Section "Avunote" MainSection
  StrCpy $ExistingInstall "0"
  StrCpy $DesktopShortcutRequested "0"
  Call ValidateInstallDir
  ${If} ${Errors}
    MessageBox MB_OK|MB_ICONSTOP "Choose a dedicated Avunote folder, not a drive root, system folder, or personal-folder root." /SD IDOK
    SetErrorLevel 2
    Abort
  ${EndIf}
  IfFileExists "$INSTDIR\*.*" 0 directory_checked
  ReadINIStr $0 "$INSTDIR\.voxriva-install.ini" "Voxriva" "Product"
  ReadINIStr $1 "$INSTDIR\.voxriva-install.ini" "Voxriva" "InstallDir"
  ${If} $0 == "Voxriva-FardinMilani-x64"
  ${AndIf} $1 == "$INSTDIR"
    StrCpy $ExistingInstall "1"
    ReadINIStr $DesktopShortcutRequested "$INSTDIR\.voxriva-install.ini" "Voxriva" "DesktopShortcut"
  ${Else}
    MessageBox MB_YESNO|MB_ICONEXCLAMATION|MB_DEFBUTTON2 "This folder is not empty and is not a registered Avunote installation. Setup may replace files with matching names. Continue?" /SD IDNO IDYES directory_checked
    SetErrorLevel 2
    Abort
  ${EndIf}
directory_checked:
  ${If} $DirectUpdate == "1"
    ReadINIStr $0 "$INSTDIR\.voxriva-install.ini" "Voxriva" "Version"
    ${If} $ExistingInstall != "1"
    ${OrIf} $0 != "$FromVersion"
      MessageBox MB_OK|MB_ICONSTOP "The installed Avunote version changed. Start the app and check for updates again."
      SetErrorLevel 2
      Abort
    ${EndIf}
  ${EndIf}
  !ifdef BASE_VERSION
    ReadINIStr $0 "$INSTDIR\.voxriva-install.ini" "Voxriva" "Version"
    ${If} $DirectUpdate != "1"
    ${OrIf} $0 != "${BASE_VERSION}"
      MessageBox MB_OK|MB_ICONSTOP "Use the matching installed Avunote version to apply this smaller update, or run the full Setup."
      SetErrorLevel 2
      Abort
    ${EndIf}
  !endif
  !insertmacro EnsureApplicationClosed "Avunote.exe" "avunote"
  !insertmacro EnsureApplicationClosed "Voxriva.exe" "legacy_voxriva"
  SetOutPath "$INSTDIR"
  ClearErrors
  File /r /x "*.log" /x "__pycache__" "${RELEASEDIR}\*"
  ${If} ${Errors}
    SetErrorLevel 2
    Abort
  ${EndIf}
  SetOutPath "$INSTDIR\Licenses\NSIS"
  File /oname=COPYING "${SOURCE_ROOT}\installer\NSIS-COPYING.txt"
  SetOutPath "$INSTDIR"
  WriteINIStr "$INSTDIR\.voxriva-install.ini" "Voxriva" "Product" "Voxriva-FardinMilani-x64"
  WriteINIStr "$INSTDIR\.voxriva-install.ini" "Voxriva" "InstallDir" "$INSTDIR"
  WriteINIStr "$INSTDIR\.voxriva-install.ini" "Voxriva" "TestMode" "$SmokeMode"
  WriteINIStr "$INSTDIR\.voxriva-install.ini" "Voxriva" "Version" "${APP_VERSION}"
  WriteINIStr "$INSTDIR\.voxriva-install.ini" "Voxriva" "DesktopShortcut" "$DesktopShortcutRequested"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  ${If} $ExistingInstall == "1"
    ; Only the recognized previous product executable is removed. Models,
    ; profile directories and unknown files are never recursively deleted.
    Delete "$INSTDIR\Voxriva.exe"
  ${EndIf}
  ${If} $SmokeMode != "1"
    ReadRegStr $0 HKCU "Software\Voxriva" "InstallDir"
    ${If} $ExistingInstall == "1"
    ${AndIf} $0 == "$INSTDIR"
      Delete "$SMPROGRAMS\Voxriva\Voxriva.lnk"
      Delete "$SMPROGRAMS\Voxriva\Uninstall Voxriva.lnk"
      RMDir "$SMPROGRAMS\Voxriva"
      ${If} $DesktopShortcutRequested == "1"
        Delete "$DESKTOP\Voxriva.lnk"
        CreateShortcut "$DESKTOP\Avunote.lnk" "$INSTDIR\Avunote.exe" "" "$INSTDIR\Avunote.exe" 0
      ${EndIf}
    ${EndIf}
    WriteRegStr HKCU "Software\Voxriva" "InstallDir" "$INSTDIR"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Voxriva" "DisplayName" "Avunote"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Voxriva" "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Voxriva" "Publisher" "Fardin Milani"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Voxriva" "InstallLocation" "$INSTDIR"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Voxriva" "DisplayIcon" "$INSTDIR\Avunote.exe,0"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Voxriva" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Voxriva" "QuietUninstallString" '$\"$INSTDIR\Uninstall.exe$\" /S'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Voxriva" "URLInfoAbout" "https://github.com/Fardinmilani"
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Voxriva" "NoModify" 1
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Voxriva" "NoRepair" 1
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Voxriva" "EstimatedSize" ${ESTIMATED_KIB}
    CreateDirectory "$SMPROGRAMS\Avunote"
    CreateShortcut "$SMPROGRAMS\Avunote\Avunote.lnk" "$INSTDIR\Avunote.exe" "" "$INSTDIR\Avunote.exe" 0
    CreateShortcut "$SMPROGRAMS\Avunote\Uninstall Avunote.lnk" "$INSTDIR\Uninstall.exe"
  ${EndIf}
  ${If} $DirectUpdate == "1"
  ${AndIf} $SmokeMode != "1"
    Exec '"$INSTDIR\Avunote.exe"'
  ${EndIf}
SectionEnd

Function un.onInit
  SetShellVarContext current
  SetRegView 64
  Call un.ValidateInstallDir
  ${If} ${Errors}
    MessageBox MB_OK|MB_ICONSTOP "The uninstall location is unsafe. No files were removed." /SD IDOK
    SetErrorLevel 2
    Abort
  ${EndIf}
  ReadINIStr $0 "$INSTDIR\.voxriva-install.ini" "Voxriva" "Product"
  ReadINIStr $1 "$INSTDIR\.voxriva-install.ini" "Voxriva" "InstallDir"
  ${If} $0 != "Voxriva-FardinMilani-x64"
  ${OrIf} $1 != "$INSTDIR"
    MessageBox MB_OK|MB_ICONSTOP "This folder is not the recorded Avunote installation. No files were removed." /SD IDOK
    SetErrorLevel 2
    Abort
  ${EndIf}
  ReadINIStr $SmokeMode "$INSTDIR\.voxriva-install.ini" "Voxriva" "TestMode"
  IfFileExists "$INSTDIR\Avunote.exe" 0 uninstall_ready
  System::Call 'kernel32::CreateFileW(w "$INSTDIR\Avunote.exe", i 0x80000000, i 0, p 0, i 3, i 0, p 0) p.r0'
  ${If} $0 == -1
    MessageBox MB_OK|MB_ICONSTOP "Close Avunote before uninstalling. No files were removed." /SD IDOK
    SetErrorLevel 2
    Abort
  ${EndIf}
  System::Call 'kernel32::CloseHandle(p r0)'
uninstall_ready:
FunctionEnd

Section "Uninstall"
  ${If} $SmokeMode != "1"
    ReadRegStr $0 HKCU "Software\Voxriva" "InstallDir"
    ${If} $0 == "$INSTDIR"
      ReadINIStr $1 "$INSTDIR\.voxriva-install.ini" "Voxriva" "DesktopShortcut"
      ${If} $1 == "1"
        Delete "$DESKTOP\Avunote.lnk"
      ${EndIf}
      Delete "$SMPROGRAMS\Avunote\Avunote.lnk"
      Delete "$SMPROGRAMS\Avunote\Uninstall Avunote.lnk"
      RMDir "$SMPROGRAMS\Avunote"
      DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Voxriva"
      DeleteRegValue HKCU "Software\Voxriva" "InstallDir"
      DeleteRegKey /ifempty HKCU "Software\Voxriva"
    ${EndIf}
  ${EndIf}
  ; Exact build-time file list only. No recursive delete and no model/data paths.
  !include "${UNINSTALL_INCLUDE}"
  Delete "$INSTDIR\Licenses\NSIS\COPYING"
  RMDir "$INSTDIR\Licenses\NSIS"
  RMDir "$INSTDIR\Licenses"
  Delete "$INSTDIR\.voxriva-install.ini"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
SectionEnd
