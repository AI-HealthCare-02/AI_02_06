param([Parameter(Mandatory=$true)][ValidateSet("local","dev","prod")][string]$e)
& "$PSScriptRoot\scripts\switch-env.ps1" $e
