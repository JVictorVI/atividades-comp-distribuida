[CmdletBinding()]
param(
    [switch]$NoBuild,
    [int]$HealthTimeoutSeconds = 120
)

$Script = Join-Path $PSScriptRoot "..\run_javascript.ps1"
$Arguments = @{
    Api = "grpc"
    StartOnly = $true
    HealthTimeoutSeconds = $HealthTimeoutSeconds
}
if ($NoBuild) {
    $Arguments.NoBuild = $true
}

& $Script @Arguments
