param(
    [string]$Command = 'id',
    [string]$Address = '10.3.81.186'
)

$projectRoot = Split-Path $PSScriptRoot -Parent
$key = Join-Path $projectRoot '.local/kindle_ed25519'
$knownHosts = Join-Path $projectRoot '.local/known_hosts'
if (!(Test-Path $key)) { throw 'Missing local Kindle SSH key.' }
& ssh -o BatchMode=yes -o IdentitiesOnly=yes -o IdentityAgent=none `
    -o ConnectTimeout=8 -o StrictHostKeyChecking=yes `
    -o "UserKnownHostsFile=$knownHosts" -i $key "root@$Address" $Command
exit $LASTEXITCODE
