Set oShell = CreateObject ("Wscript.Shell") 
Dim strArgs
strArgs = "cmd /c startup.bat"
oShell.Run strArgs, 0, false