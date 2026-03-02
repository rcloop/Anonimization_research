# Privacy suite: corpus v1, sin canary insertion, con similitud semántica
# Ejecutar desde la raíz del proyecto o desde src/privacy_evaluation

$ErrorActionPreference = "Stop"
$ScriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$ProjectRoot = Split-Path (Split-Path $ScriptDir -Parent) -Parent
$CorpusV1 = Join-Path (Join-Path $ProjectRoot "corpus_repo") "corpus_v1"
$OutputDir = Join-Path $ScriptDir "privacy_evaluation_results_v1"

if (-not (Test-Path $CorpusV1)) {
    Write-Error "No se encontró corpus v1 en: $CorpusV1"
    exit 1
}

Set-Location $ScriptDir
Write-Host "Corpus: $CorpusV1"
Write-Host "Salida: $OutputDir"
Write-Host "Opciones: sin canary, con similitud semantica"
Write-Host ""

& python run_all_privacy_evaluations.py `
    --corpus_path $CorpusV1 `
    --annotations_path (Join-Path $CorpusV1 "entidades") `
    --output_dir $OutputDir `
    --skip_canary

Set-Location $ProjectRoot
