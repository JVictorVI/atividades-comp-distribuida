[CmdletBinding()]
param(
    [switch]$NoBuild,
    [int]$HealthTimeoutSeconds = 120
)

$Script = Join-Path $PSScriptRoot "..\run_python.ps1"
$Arguments = @{
    Api = "graphql"
    StartOnly = $true
    HealthTimeoutSeconds = $HealthTimeoutSeconds
}
if ($NoBuild) {
    $Arguments.NoBuild = $true
}

& $Script @Arguments
