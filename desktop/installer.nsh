!include LogicLib.nsh

!macro customInstall
  DetailPrint "Preparing Python runtime and Simple Signal dependencies..."
  ExecWait '"$SYSDIR\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\bootstrap-runtime.ps1" -InstallDir "$INSTDIR" -Unattended' $0
  ${If} $0 != 0
    MessageBox MB_ICONEXCLAMATION|MB_OK "Simple Signal was installed, but Python dependency setup did not complete successfully.$\r$\n$\r$\nLog file:$\r$\n$INSTDIR\simple-signal-bootstrap.log"
  ${EndIf}
!macroend
