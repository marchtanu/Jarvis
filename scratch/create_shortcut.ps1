$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = [System.IO.Path]::Combine($DesktopPath, "auhip.lnk")
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)

$ProjectDir = "D:\Desktop\Code\personal\project\Jarvis_demo"
$PythonExe = [System.IO.Path]::Combine($ProjectDir, ".venv", "Scripts", "python.exe")
$ScriptPath = [System.IO.Path]::Combine($ProjectDir, "main.py")

$Shortcut.TargetPath = $PythonExe
$Shortcut.Arguments = "`"$ScriptPath`""
$Shortcut.WorkingDirectory = $ProjectDir
$Shortcut.Description = "Run auhip Assistant"
$Shortcut.IconLocation = "$ProjectDir\auhip_icon.ico"
$Shortcut.Save()

Write-Host "Shortcut created on Desktop: $ShortcutPath"
