' Hidden launcher for the nightly Steam crawl.
' The scheduled task starts this file with wscript.exe, so cmd.exe never
' shows a console window: the crawl runs for ~25 minutes and a visible
' window invites the user to close it, which kills the update mid-way.
'
' Target: run-daily.bat in this same folder. We wait for it so the task
' stays "Running" while the crawl works and Task Scheduler records the
' real exit code (0 = data written, non-zero = previous data kept).

Dim fso, shell, here, target, code
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

here = fso.GetParentFolderName(WScript.ScriptFullName)
target = here & "\run-daily.bat"

If fso.FileExists(target) Then
  code = shell.Run("""" & target & """", 0, True)
  WScript.Quit code
Else
  shell.Run "cmd /c echo [%date% %time%] run-daily.bat missing >> """ & here & "\..\data\crawler.log""", 0, True
  WScript.Quit 1
End If
