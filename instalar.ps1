# instalar.ps1 - prepara o PC para o projeto Familias GSVL
# Uso (PowerShell):  powershell -ExecutionPolicy Bypass -File C:\familias-revit\instalar.ps1
# Faz: confere git/python/pyRevit, acha Revit e templates, ajusta config.json,
# registra a extensao no pyRevit, roda os validadores e grava output\logs\diagnostico_*.txt
param([string]$Repo = $PSScriptRoot)

$logDir = Join-Path $Repo 'output\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ('diagnostico_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.txt')
function Diz([string]$t) { Write-Host $t; Add-Content -Path $log -Value $t -Encoding UTF8 }

Diz "== Familias GSVL - diagnostico $(Get-Date) =="
Diz "Repositorio: $Repo"

# 1) Programas
Diz ''
Diz '== Programas =='
$faltando = @()
foreach ($c in @('git', 'python', 'pyrevit')) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd) {
        $v = (& $c --version 2>&1 | Select-Object -First 1)
        Diz ("OK     {0}: {1}" -f $c, $v)
    } else {
        Diz ("FALTA  {0}" -f $c)
        $faltando += $c
    }
}

# 2) Revit instalado
Diz ''
Diz '== Revit =='
$revits = Get-ChildItem 'C:\Program Files\Autodesk' -Directory -Filter 'Revit 20*' -ErrorAction SilentlyContinue | Sort-Object Name
foreach ($r in $revits) { Diz ("Instalado: {0}" -f $r.FullName) }
if (-not $revits) { Diz 'Nenhum Revit encontrado em C:\Program Files\Autodesk' }

# 3) Templates (familia .rft e projeto .rte)
Diz ''
Diz '== Templates =='
$rvts = Get-ChildItem 'C:\ProgramData\Autodesk' -Directory -Filter 'RVT 20*' -ErrorAction SilentlyContinue | Sort-Object Name
$escolhido = $null
foreach ($d in $rvts) {
    $fam = Join-Path $d.FullName 'Family Templates'
    $prj = Join-Path $d.FullName 'Templates'
    $nRft = @(Get-ChildItem $fam -Recurse -Filter '*.rft' -ErrorAction SilentlyContinue).Count
    $nRte = @(Get-ChildItem $prj -Recurse -Filter '*.rte' -ErrorAction SilentlyContinue).Count
    Diz ("{0}: {1} templates de familia, {2} de projeto" -f $d.Name, $nRft, $nRte)
    foreach ($sub in Get-ChildItem $fam -Directory -ErrorAction SilentlyContinue) { Diz ("    idioma/pasta: {0}" -f $sub.Name) }
    Get-ChildItem $fam -Recurse -Filter '*.rft' -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match 'obili|urniture|anela|indow' } |
        ForEach-Object { Diz ("    rft: {0}" -f $_.FullName.Substring($fam.Length + 1)) }
    Get-ChildItem $prj -Recurse -Filter '*.rte' -ErrorAction SilentlyContinue |
        ForEach-Object { Diz ("    rte: {0}" -f $_.FullName.Substring($prj.Length + 1)) }
    if ($nRft -gt 0) { $escolhido = $d }
}

# 4) config.json -> versao mais nova com templates
if ($escolhido) {
    $cfgPath = Join-Path $Repo 'config.json'
    $cfg = Get-Content $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $cfg.revit_versao = $escolhido.Name.Replace('RVT ', '')
    $cfg.templates_dir = Join-Path $escolhido.FullName 'Family Templates'
    $cfg | Add-Member -NotePropertyName templates_projeto_dir -NotePropertyValue (Join-Path $escolhido.FullName 'Templates') -Force
    $json = $cfg | ConvertTo-Json -Depth 5
    [System.IO.File]::WriteAllText($cfgPath, $json, (New-Object System.Text.UTF8Encoding($false)))
    Diz ''
    Diz ("config.json ajustado para {0}" -f $escolhido.Name)
}

# 5) pyRevit: registrar a extensao
Diz ''
Diz '== pyRevit =='
if (Get-Command pyrevit -ErrorAction SilentlyContinue) {
    Diz ((& pyrevit attached 2>&1) -join "`n")
    Diz ((& pyrevit extensions paths add $Repo 2>&1) -join "`n")
    Diz ((& pyrevit extensions paths 2>&1) -join "`n")
} else {
    Diz 'pyRevit nao encontrado - extensao nao registrada'
}

# 6) Validadores (fora do Revit)
if (Get-Command python -ErrorAction SilentlyContinue) {
    Diz ''
    Diz '== Validadores =='
    Diz ((& python (Join-Path $Repo 'tools\validar_specs.py') 2>&1) -join "`n")
    Diz ((& python (Join-Path $Repo 'tools\validar_casa.py') 2>&1) -join "`n")
}

# 7) O que falta
Diz ''
if ($faltando.Count -gt 0) {
    Diz '== FALTA INSTALAR =='
    if ($faltando -contains 'git')     { Diz 'git:     winget install --id Git.Git -e' }
    if ($faltando -contains 'python')  { Diz 'python:  winget install --id Python.Python.3.12 -e   (depois feche e reabra o PowerShell)' }
    if ($faltando -contains 'pyrevit') { Diz 'pyRevit: baixe o instalador em https://github.com/pyrevitlabs/pyRevit/releases (versao que suporte o seu Revit) e rode este script de novo' }
} else {
    Diz 'Tudo instalado. Feche e reabra o Revit; deve aparecer a aba FamiliasGSVL com o botao Rodar Tudo.'
}
Diz ''
Diz "Diagnostico salvo em: $log"
