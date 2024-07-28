!addplugindir /x86-ansi "..\\..\\windows\\installer-gui\\Plugins\x86-ansi"
!addplugindir /x86-unicode "..\\..\\windows\\installer-gui\\Plugins\x86-unicode"
!addincludedir "..\\..\\windows\\installer-gui\\Include"
!addincludedir "..\\..\\windows\\installer-gui\\Common"

; Includes
!include MUI2.nsh
!include UAC.nsh
!include NsisMultiUser.nsh
!include LogicLib.nsh
!include StdUtils.nsh

; Installer defines
!define PRODUCT_NAME "[[ib.appname]]"
!define VERSION "[[ib.version]]"
!define ICON "[[icon]]"
!define COMPANY_NAME "[[ib.appname]]"
!define CONTACT "@jackzzs"
!define URL_INFO_ABOUT "https://github.com/zetxtech/embykeeper"
!define URL_HELP_LINK "https://github.com/zetxtech/embykeeper/wiki"
!define URL_UPDATE_INFO "https://github.com/zetxtech/embykeeper/releases"
!define PLATFORM "Win"
!define MIN_WIN_VER "XP"
!define SETUP_MUTEX "${COMPANY_NAME} ${PRODUCT_NAME} Setup Mutex"
!define APP_MUTEX "${COMPANY_NAME} ${PRODUCT_NAME} App Mutex"
!define SETTINGS_REG_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define LICENSE_FILE "[[license_file]]"
!define CONFIG_FILE_DIR "%LOCALAPPDATA%\embykeeper\embykeeper"


!define MULTIUSER_INSTALLMODE_ALLOW_BOTH_INSTALLATIONS 0
!define MULTIUSER_INSTALLMODE_ALLOW_ELEVATION 0
!define MULTIUSER_INSTALLMODE_DEFAULT_ALLUSERS 0
!define MULTIUSER_INSTALLMODE_64_BIT 1
!define MULTIUSER_INSTALLMODE_DISPLAYNAME "${PRODUCT_NAME} ${VERSION}"

; Variables
Var StartMenuFolder

; Installer Attributes
Name "${PRODUCT_NAME} v${VERSION}"
OutFile "${PRODUCT_NAME}.exe"
BrandingText "${COMPANY_NAME} Copyright 2023"

AllowSkipFiles off
SetOverwrite on ; (default setting) set to on except for where it is manually switched off
ShowInstDetails show
Unicode true ; properly display all languages (Installer will not work on Windows 95, 98 or ME!)
SetCompressor /SOLID lzma

!include Utils.nsh

; Interface Settings
!define MUI_ABORTWARNING ; Show a confirmation when cancelling the installation
!define MUI_LANGDLL_ALLLANGUAGES ; Show all languages, despite user's codepage
!define MUI_ICON "[[icon]]"
!define MUI_UNICON "[[icon]]"

; Remember the installer language
!define MUI_LANGDLL_REGISTRY_ROOT SHCTX
!define MUI_LANGDLL_REGISTRY_KEY "${SETTINGS_REG_KEY}"
!define MUI_LANGDLL_REGISTRY_VALUENAME "Language"

; Pages
!define MUI_PAGE_CUSTOMFUNCTION_PRE PageWelcomeLicensePre
!insertmacro MUI_PAGE_WELCOME

!ifdef LICENSE_FILE
	!define MUI_PAGE_CUSTOMFUNCTION_PRE PageWelcomeLicensePre
	!insertmacro MUI_PAGE_LICENSE "${LICENSE_FILE}"
!endif

!define MULTIUSER_INSTALLMODE_CHANGE_MODE_FUNCTION PageInstallModeChangeMode
!insertmacro MULTIUSER_PAGE_INSTALLMODE

!define MUI_COMPONENTSPAGE_SMALLDESC
!define MUI_PAGE_CUSTOMFUNCTION_PRE PageComponentsPre
!insertmacro MUI_PAGE_COMPONENTS

!define MUI_PAGE_CUSTOMFUNCTION_PRE PageDirectoryPre
!define MUI_PAGE_CUSTOMFUNCTION_SHOW PageDirectoryShow
!insertmacro MUI_PAGE_DIRECTORY

!define MUI_STARTMENUPAGE_NODISABLE ; Do not display the checkbox to disable the creation of Start Menu shortcuts
!define MUI_STARTMENUPAGE_DEFAULTFOLDER "${PRODUCT_NAME}"
!define MUI_STARTMENUPAGE_REGISTRY_ROOT SHCTX ; writing to $StartMenuFolder happens in MUI_STARTMENU_WRITE_END, so it's safe to use SHCTX here
!define MUI_STARTMENUPAGE_REGISTRY_KEY "${SETTINGS_REG_KEY}"
!define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "StartMenuFolder"
!define MUI_PAGE_CUSTOMFUNCTION_PRE PageStartMenuPre
!insertmacro MUI_PAGE_STARTMENU "" "$StartMenuFolder"
!define MUI_STARTMENUPAGE_DEFAULTFOLDER "${PRODUCT_NAME}" ; the MUI_PAGE_STARTMENU macro undefines MUI_STARTMENUPAGE_DEFAULTFOLDER, but we need it

!define MUI_PAGE_CUSTOMFUNCTION_SHOW PageInstFilesPre
!insertmacro MUI_PAGE_INSTFILES

!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_FUNCTION PageFinishRun
!insertmacro MUI_PAGE_FINISH

; Installer Attributes
ShowUninstDetails show

; Pages
!insertmacro MULTIUSER_UNPAGE_INSTALLMODE

UninstPage components un.PageComponentsPre un.PageComponentsShow un.EmptyCallback

UninstPage instfiles

; Languages (first is default language) - must be inserted after all pages
!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "English"
!insertmacro MULTIUSER_LANGUAGE_INIT

; Reserve files
!insertmacro MUI_RESERVEFILE_LANGDLL

; Functions
Function CheckInstallation
	; if there's an installed version, uninstall it first (I chose not to start the uninstaller silently, so that user sees what failed)
	; if both per-user and per-machine versions are installed, unistall the one that matches $MultiUser.InstallMode
	StrCpy $0 ""
	${if} $HasCurrentModeInstallation = 1
		StrCpy $0 "$MultiUser.InstallMode"
	${else}
		!if ${MULTIUSER_INSTALLMODE_ALLOW_BOTH_INSTALLATIONS} = 0
			${if} $HasPerMachineInstallation = 1
				StrCpy $0 "AllUsers" ; if there's no per-user installation, but there's per-machine installation, uninstall it
			${elseif} $HasPerUserInstallation = 1
				StrCpy $0 "CurrentUser" ; if there's no per-machine installation, but there's per-user installation, uninstall it
			${endif}
		!endif
	${endif}

	${if} "$0" != ""
		${if} $0 == "AllUsers"
			StrCpy $1 "$PerMachineUninstallString"
			StrCpy $3 "$PerMachineInstallationFolder"
		${else}
			StrCpy $1 "$PerUserUninstallString"
			StrCpy $3 "$PerUserInstallationFolder"
		${endif}
		${if} ${silent}
			StrCpy $2 "/S"
		${else}
			StrCpy $2 ""
		${endif}
	${endif}
FunctionEnd

Function RunUninstaller
	StrCpy $0 0
	ExecWait '$1 /SS $2 _?=$3' $0 ; $1 is quoted in registry; the _? param stops the uninstaller from copying itself to the temporary directory, which is the only way for ExecWait to work
FunctionEnd

; Sections
InstType "完整安装"

Section "Embykeeper 核心文件 (必须)" SectionCoreFiles
	SectionIn 1 2 3 RO

	!insertmacro UAC_AsUser_Call Function CheckInstallation ${UAC_SYNCREGISTERS}
	${if} $0 != ""
		HideWindow
		ClearErrors
		${if} $0 == "AllUsers"
			Call RunUninstaller
  		${else}
			!insertmacro UAC_AsUser_Call Function RunUninstaller ${UAC_SYNCREGISTERS}
  		${endif}
		${if} ${errors} ; stay in installer
			SetErrorLevel 2 ; Installation aborted by script
			BringToFront
			Abort "Error executing uninstaller."
		${else}
			${Switch} $0
				${Case} 0 ; uninstaller completed successfully - continue with installation
					BringToFront
					Sleep 1000 ; wait for cmd.exe (called by the uninstaller) to finish
					${Break}
				${Case} 1 ; Installation aborted by user (cancel button)
				${Case} 2 ; Installation aborted by script
					SetErrorLevel $0
					Quit ; uninstaller was started, but completed with errors - Quit installer
				${Default} ; all other error codes - uninstaller could not start, elevate, etc. - Abort installer
					SetErrorLevel $0
					BringToFront
					Abort "Error executing uninstaller."
			${EndSwitch}
		${endif}

		; Just a failsafe - should've been taken care of by cmd.exe
		!insertmacro DeleteRetryAbort "$3\${UNINSTALL_FILENAME}" ; the uninstaller doesn't delete itself when not copied to the temp directory
		RMDir "$3"
	${endif}

	[% block install_pkgs %]
		SetOutPath "$INSTDIR\pkgs"
		File /r "pkgs\*.*"
	[% endblock install_pkgs %]

	SetOutPath "$INSTDIR"

	[% block install_files %]
	; Install files
	[% for destination, group in grouped_files %]
		SetOutPath "[[destination]]"
		[% for file in group %]
		File "[[ file ]]"
		[% endfor %]
	[% endfor %]

	; Install directories
	[% for dir, destination in ib.install_dirs %]
		SetOutPath "[[ pjoin(destination, dir) ]]"
		File /r "[[dir]]\*.*"
	[% endfor %]
	[% endblock install_files %]

	; Byte-compile Python files.
	DetailPrint "正在编译 Python 模块 ..."
	nsExec::ExecToLog '[[ python ]] -m compileall -q "$INSTDIR\pkgs"'

	; Uninstaller
	WriteUninstaller $INSTDIR\uninstall.exe

	; License
	!ifdef LICENSE_FILE
		File "${LICENSE_FILE}"
	!endif

	; Registry
	!insertmacro MULTIUSER_RegistryAddInstallInfo
SectionEnd

SectionGroup /e "快捷方式" SectionGroupIntegration
Section "开始菜单文件夹" SectionProgramGroup
	SectionIn 1 3

	!insertmacro MUI_STARTMENU_WRITE_BEGIN ""

		CreateDirectory "$SMPROGRAMS\$StartMenuFolder"

		[% for scname, sc in ib.shortcuts.items() %]
		CreateShortCut "$SMPROGRAMS\$StartMenuFolder\[[scname]].lnk" "[[sc['target'] ]]" '[[ sc['parameters'] ]]' "$INSTDIR\[[ sc['icon'] ]]"
		[% endfor %]

		!ifdef LICENSE_FILE
			CreateShortCut "$SMPROGRAMS\$StartMenuFolder\开源授权.lnk" "$INSTDIR\${LICENSE_FILE}"
		!endif

		!ifdef CONFIG_FILE_DIR
			CreateShortCut "$SMPROGRAMS\$StartMenuFolder\数据目录.lnk" "${CONFIG_FILE_DIR}"
			CreateShortCut "$SMPROGRAMS\$StartMenuFolder\配置文件.lnk" "${CONFIG_FILE_DIR}\config.toml"
		!endif

		WriteINIStr "$SMPROGRAMS\$StartMenuFolder\项目主页.url" "InternetShortcut" "URL" "${URL_INFO_ABOUT}"
		WriteINIStr "$SMPROGRAMS\$StartMenuFolder\部署帮助.url" "InternetShortcut" "URL" "${URL_HELP_LINK}"
		WriteINIStr "$SMPROGRAMS\$StartMenuFolder\检查更新.url" "InternetShortcut" "URL" "${URL_UPDATE_INFO}"

		${if} $MultiUser.InstallMode == "AllUsers"
			CreateShortCut "$SMPROGRAMS\$StartMenuFolder\卸载.lnk" "$INSTDIR\${UNINSTALL_FILENAME}" "/allusers"
		${else}
			CreateShortCut "$SMPROGRAMS\$StartMenuFolder\卸载.lnk" "$INSTDIR\${UNINSTALL_FILENAME}" "/currentuser"
		${endif}

	!insertmacro MUI_STARTMENU_WRITE_END
SectionEnd

Section "桌面快捷方式" SectionDesktopIcon
	SectionIn 1 3

	!insertmacro MULTIUSER_GetCurrentUserString $0

	[% for scname, sc in ib.shortcuts.items() %]
	CreateShortCut "$DESKTOP\${PRODUCT_NAME}$0.lnk" "[[sc['target'] ]]" '[[ sc['parameters'] ]]' "$INSTDIR\[[ sc['icon'] ]]"
	[% endfor %]
SectionEnd

SectionGroupEnd

Section "-Write Install Size" ; hidden section, write install size as the final step
	!insertmacro MULTIUSER_RegistryAddInstallSizeInfo
SectionEnd

; Modern install component descriptions
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
	!insertmacro MUI_DESCRIPTION_TEXT ${SectionCoreFiles} "运行 ${PRODUCT_NAME} 所需的核心文件."
	!insertmacro MUI_DESCRIPTION_TEXT ${SectionGroupIntegration} "选择如何创建快捷方式以启动."
	!insertmacro MUI_DESCRIPTION_TEXT ${SectionProgramGroup} "在开始菜单创建一个 ${PRODUCT_NAME} 文件夹."
	!insertmacro MUI_DESCRIPTION_TEXT ${SectionDesktopIcon} "在桌面创建一个 ${PRODUCT_NAME} 图标."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; Callbacks
Function .onInit
	!insertmacro CheckPlatform ${PLATFORM}
	!insertmacro CheckMinWinVer ${MIN_WIN_VER}
	${ifnot} ${UAC_IsInnerInstance}
		!insertmacro CheckSingleInstance "Setup" "Global" "${SETUP_MUTEX}"
		!insertmacro CheckSingleInstance "Application" "Local" "${APP_MUTEX}"
	${endif}

	!insertmacro MULTIUSER_INIT

	${if} $IsInnerInstance = 0
		!insertmacro MUI_LANGDLL_DISPLAY
	${endif}
FunctionEnd

Function PageWelcomeLicensePre
	${if} $InstallShowPagesBeforeComponents = 0
		Abort ; don't display the Welcome and License pages
	${endif}
FunctionEnd

Function PageInstallModeChangeMode
	!insertmacro MUI_STARTMENU_GETFOLDER "" $StartMenuFolder

	${if} "$StartMenuFolder" == "${MUI_STARTMENUPAGE_DEFAULTFOLDER}"
		!insertmacro MULTIUSER_GetCurrentUserString $0
		StrCpy $StartMenuFolder "$StartMenuFolder$0"
	${endif}
FunctionEnd

Function PageComponentsPre
	GetDlgItem $0 $HWNDPARENT 1
	SendMessage $0 ${BCM_SETSHIELD} 0 0 ; hide SHIELD (Windows Vista and above)
FunctionEnd

Function PageDirectoryPre
	GetDlgItem $1 $HWNDPARENT 1
	${if} ${SectionIsSelected} ${SectionProgramGroup}
		SendMessage $1 ${WM_SETTEXT} 0 "STR:$(^NextBtn)" ; this is not the last page before installing
		SendMessage $1 ${BCM_SETSHIELD} 0 0 ; hide SHIELD (Windows Vista and above)
	${else}
		SendMessage $1 ${WM_SETTEXT} 0 "STR:$(^InstallBtn)" ; this is the last page before installing
		Call MultiUser.CheckPageElevationRequired
		${if} $0 = 2
			SendMessage $1 ${BCM_SETSHIELD} 0 1 ; display SHIELD (Windows Vista and above)
		${endif}
	${endif}
FunctionEnd

Function PageDirectoryShow
	${if} $CmdLineDir != ""
		FindWindow $R1 "#32770" "" $HWNDPARENT

		GetDlgItem $0 $R1 1019 ; Directory edit
		SendMessage $0 ${EM_SETREADONLY} 1 0 ; read-only is better than disabled, as user can copy contents

		GetDlgItem $0 $R1 1001 ; Browse button
		EnableWindow $0 0
	${endif}
FunctionEnd

Function PageStartMenuPre
	${ifnot} ${SectionIsSelected} ${SectionProgramGroup}
		Abort ; don't display this dialog if SectionProgramGroup is not selected
	${else}
		GetDlgItem $1 $HWNDPARENT 1
		Call MultiUser.CheckPageElevationRequired
		${if} $0 = 2
			SendMessage $1 ${BCM_SETSHIELD} 0 1 ; display SHIELD (Windows Vista and above)
		${endif}
	${endif}
FunctionEnd

Function PageInstFilesPre
	GetDlgItem $0 $HWNDPARENT 1
	SendMessage $0 ${BCM_SETSHIELD} 0 0 ; hide SHIELD (Windows Vista and above)
FunctionEnd

Function PageFinishRun
	; the installer might exit too soon before the application starts and it loses the right to be the foreground window and starts in the background
	; however, if there's no active window when the application starts, it will become the active window, so we hide the installer
	HideWindow
	; the installer will show itself again quickly before closing (w/o Taskbar button), we move it offscreen
	!define SWP_NOSIZE 0x0001
	!define SWP_NOZORDER 0x0004
	System::Call "User32::SetWindowPos(i, i, i, i, i, i, i) b ($HWNDPARENT, 0, -1000, -1000, 0, 0, ${SWP_NOZORDER}|${SWP_NOSIZE})"

	[% for scname, sc in ib.shortcuts.items() %]
	[% if loop.first %]
	!insertmacro UAC_AsUser_ExecShell "open" "[[sc['target'] ]]" '[[ sc['parameters'] ]]' "$INSTDIR" ""
	[% endif %]
	[% endfor %]
FunctionEnd

Function .onInstFailed
	MessageBox MB_ICONSTOP "${PRODUCT_NAME} ${VERSION} could not be fully installed.$\r$\nPlease, restart Windows and run the setup program again." /SD IDOK
FunctionEnd

; ==========================================================================================
; Uninstaller
; ==========================================================================================

!insertmacro DeleteRetryAbortFunc "un."
!insertmacro CheckSingleInstanceFunc "un."

; Variables
Var SemiSilentMode ; installer started uninstaller in semi-silent mode using /SS parameter
Var RunningFromInstaller ; installer started uninstaller using /uninstall parameter
Var RunningAsShellUser ; uninstaller restarted itself under the user of the running shell

Section "un.程序文件" SectionUninstallProgram
	SectionIn RO

	!insertmacro MULTIUSER_GetCurrentUserString $0

	[% block uninstall_files %]
    ; Uninstall files
    [% for file, destination in ib.install_files %]
        !insertmacro DeleteRetryAbort "[[pjoin(destination, file)]]"
    [% endfor %]
    ; Uninstall directories
    [% for dir, destination in ib.install_dirs %]
        RMDir /r "[[pjoin(destination, dir)]]"
    [% endfor %]
    [% endblock uninstall_files %]

    ; Clean up "Pkgs"
    RMDir /r "$INSTDIR\pkgs"

	; Clean up "Program Group"
	RMDir /r "$SMPROGRAMS\${PRODUCT_NAME}$0"

	; Clean up "Desktop Icon"
	!insertmacro DeleteRetryAbort "$DESKTOP\${PRODUCT_NAME}$0.lnk"
SectionEnd

Section /o "un.配置和数据文件" SectionRemoveSettings
	RMDir /r "${CONFIG_FILE_DIR}"
SectionEnd

Section "-Uninstall" ; hidden section, must always be the last one!
	!insertmacro MULTIUSER_RegistryRemoveInstallInfo

	Delete "$INSTDIR\${UNINSTALL_FILENAME}" ; we cannot use un.DeleteRetryAbort here - when using the _? parameter the uninstaller cannot delete itself and Delete fails, which is OK
	; remove the directory only if it is empty - the user might have saved some files in it
	RMDir "$INSTDIR"

	; Remove the uninstaller from registry as the very last step - if sth. goes wrong, let the user run it again
	!insertmacro MULTIUSER_RegistryRemoveInstallInfo ; Remove registry keys

	; If the uninstaller still exists, use cmd.exe on exit to remove it (along with $INSTDIR if it's empty)
	${if} ${FileExists} "$INSTDIR\${UNINSTALL_FILENAME}"
		Exec 'cmd.exe /c (del /f /q "$INSTDIR\${UNINSTALL_FILENAME}") && (rmdir "$INSTDIR")'
	${endif}
SectionEnd

; Callbacks
Function un.onInit
	${GetParameters} $R0

	${GetOptions} $R0 "/uninstall" $R1
	${ifnot} ${errors}
		StrCpy $RunningFromInstaller 1
	${else}
		StrCpy $RunningFromInstaller 0
	${endif}

	${GetOptions} $R0 "/SS" $R1
	${ifnot} ${errors}
		StrCpy $SemiSilentMode 1
		StrCpy $RunningFromInstaller 1
		SetAutoClose true ; auto close (if no errors) if we are called from the installer; if there are errors, will be automatically set to false
	${else}
		StrCpy $SemiSilentMode 0
	${endif}

	${GetOptions} $R0 "/shelluser" $R1
	${ifnot} ${errors}
		StrCpy $RunningAsShellUser 1
	${else}
		StrCpy $RunningAsShellUser 0
	${endif}

	${ifnot} ${UAC_IsInnerInstance}
	${andif} $RunningFromInstaller = 0
		; Restarting the uninstaller using the user of the running shell, in order to overcome the Windows bugs that:
		; - Elevates the uninstallers of single-user installations when called from 'Apps & features' of Windows 10
		; causing them to fail when using a different account for elevation.
		; - Elevates the uninstallers of all-users installations when called from 'Add/Remove Programs' of Control Panel,
		; preventing them of eleveting on their own and correctly recognize the user that started the uninstaller. If a
		; different account was used for elevation, all user-context operations will be performed for the user of that
		; account. In this case, the fix causes the elevetion prompt to be displayed twice (one from Control Panel and
		; one from the uninstaller).
		${if} ${UAC_IsAdmin}
		${andif} $RunningAsShellUser = 0
			${StdUtils.ExecShellAsUser} $0 "$INSTDIR\${UNINSTALL_FILENAME}" "open" "/shelluser $R0"
			Quit
		${endif}
		!insertmacro CheckSingleInstance "Setup" "Global" "${SETUP_MUTEX}"
		!insertmacro CheckSingleInstance "Application" "Local" "${APP_MUTEX}"
	${endif}

	!insertmacro MULTIUSER_UNINIT
FunctionEnd

Function un.EmptyCallback
FunctionEnd

Function un.PageComponentsPre
	${if} $SemiSilentMode = 1
		Abort ; if user is installing, no use to remove program settings anyway (should be compatible with all versions)
	${endif}
FunctionEnd

Function un.PageComponentsShow
	; Show/hide the Back button
	GetDlgItem $0 $HWNDPARENT 3
	ShowWindow $0 $UninstallShowBackButton
FunctionEnd

Function un.onUninstFailed
	${if} $SemiSilentMode = 0
		MessageBox MB_ICONSTOP "${PRODUCT_NAME} ${VERSION} could not be fully uninstalled.$\r$\nPlease, restart Windows and run the uninstaller again." /SD IDOK
	${else}
		MessageBox MB_ICONSTOP "${PRODUCT_NAME} could not be fully installed.$\r$\nPlease, restart Windows and run the setup program again." /SD IDOK
	${endif}
FunctionEnd
