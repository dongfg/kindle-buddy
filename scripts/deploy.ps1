param([string]$Address = '10.3.81.186')
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$options = @('-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes', '-o', 'IdentityAgent=none',
    '-o', 'StrictHostKeyChecking=yes', '-o', "UserKnownHostsFile=$root/.local/known_hosts",
    '-i', "$root/.local/kindle_ed25519")
& ssh @options "root@$Address" 'mkdir -p /mnt/us/kindle-buddy'
if ($LASTEXITCODE) { throw 'Cannot reach Kindle.' }
$files = @('buddy.py', 'start.sh', 'stop.sh', 'config.json', 'sync_time.py', 'launch.sh', 'make_cover.py', 'power_schedule.py', 'sleep-cat.png', 'cat-icon.png') | ForEach-Object { Join-Path $root "device/$_" }
# -O selects classic SCP, supported by the Kindle USBNetwork package.
& scp -O @options @files "root@${Address}:/mnt/us/kindle-buddy/"
if ($LASTEXITCODE) { throw 'Upload failed.' }
& scp -O -r @options "$root/device/vendor" "root@${Address}:/mnt/us/kindle-buddy/"
if ($LASTEXITCODE) { throw 'Dependency upload failed.' }
& ssh @options "root@$Address" '/mnt/us/python3/bin/python3.9 /mnt/us/kindle-buddy/make_cover.py'
if ($LASTEXITCODE) { throw 'Cover generation failed.' }
& scp -O @options "$root/device/KindleBuddy.sh" "root@${Address}:/mnt/us/documents/KindleBuddy.sh"
if ($LASTEXITCODE) { throw 'Library launcher upload failed.' }
& ssh @options "root@$Address" '/mnt/us/python3/bin/python3.9 /mnt/us/kindle-buddy/buddy.py --self-test'
if ($LASTEXITCODE) { throw 'Device checks failed.' }
Write-Host 'Uploaded. Start with scripts/kindle.ps1; see DEVELOP.md.'
