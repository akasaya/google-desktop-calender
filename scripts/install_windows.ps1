param(
    [Parameter(Mandatory=$true)][string]$ExePath,
    [string]$CredentialSource,
    [switch]$AutoStart
)
$ErrorActionPreference = 'Stop'
$installDir = Join-Path $env:LOCALAPPDATA 'Programs\GoogleDesktopCalendar'
New-Item -ItemType Directory -Path $installDir -Force | Out-Null
$target = Join-Path $installDir 'GoogleDesktopCalendar.exe'
Copy-Item -LiteralPath $ExePath -Destination $target -Force

# Keep this script ASCII-compatible for Windows PowerShell 5.1.
# Discover the config directory using the executable's own smoke report.
$report = Join-Path $env:TEMP ('gdc-install-' + [guid]::NewGuid() + '.json')
$process = Start-Process -FilePath $target -ArgumentList @('--demo', '--smoke-report', ('"' + $report + '"')) -PassThru
if (-not $process.WaitForExit(120000)) { $process.Kill(); throw 'Executable did not exit' }
if (-not (Test-Path $report)) { throw 'Executable failed to launch' }
$result = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
Remove-Item -LiteralPath $report
if (-not $result.success -or $result.qt_platform -ne 'windows') { throw 'Windows GUI validation failed' }

if ($CredentialSource) {
    $configDir = $result.config_dir
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
    $token = Join-Path $configDir 'token.json'
    if (Test-Path $token) { throw 'Existing Windows credentials were preserved. Omit CredentialSource to keep them.' }
    Copy-Item -LiteralPath $CredentialSource -Destination $token
    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $acl = Get-Acl -LiteralPath $token
    $acl.SetAccessRuleProtection($true, $false)
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($identity, 'FullControl', 'Allow')
    $acl.AddAccessRule($rule)
    Set-Acl -LiteralPath $token -AclObject $acl
}

$shell = New-Object -ComObject WScript.Shell
$shortcutName = 'Google Desktop Calendar.lnk'
$folders = @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))
if ($AutoStart) { $folders += [Environment]::GetFolderPath('Startup') }
foreach ($folder in $folders) {
    $shortcut = $shell.CreateShortcut((Join-Path $folder $shortcutName))
    $shortcut.TargetPath = $target
    $shortcut.WorkingDirectory = $installDir
    $shortcut.IconLocation = $target + ',0'
    $shortcut.Description = 'Google Desktop Calendar'
    $shortcut.Save()
}
[pscustomobject]@{Executable=$target; ConfigDirectory=$result.config_dir; AutoStart=[bool]$AutoStart} | ConvertTo-Json -Compress
