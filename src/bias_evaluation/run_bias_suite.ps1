$ErrorActionPreference = "Stop"

$ScriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }

param(
    [Parameter(Mandatory = $true)]
    [string]$DataPath,

    [Parameter(Mandatory = $true)]
    [string]$SensitiveCol,

    [Parameter(Mandatory = $false)]
    [string]$OutputPath = "bias_evaluation_results/bias_report.json",

    [Parameter(Mandatory = $false)]
    [double]$Threshold = 0.5
)

Set-Location $ScriptDir

# Activar venv (recomendado)
if (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
} else {
    Write-Host "ERROR: venv no encontrado. Ejecuta: python setup_venv.py" -ForegroundColor Red
    exit 1
}

python run_bias_suite.py `
    --data_path $DataPath `
    --sensitive_col $SensitiveCol `
    --output_path $OutputPath `
    --threshold $Threshold

