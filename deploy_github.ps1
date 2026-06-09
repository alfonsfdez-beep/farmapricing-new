# =============================================================
# Script de despliegue a GitHub
# Crea el repo, inicializa git, primer commit y push.
#
# Uso (PowerShell desde la carpeta app/):
#   .\deploy_github.ps1
#
# Pre-requisitos:
#   - Git instalado (https://git-scm.com/download/win)
#   - PAT con permiso 'repo' (lo pega en pantalla cuando lo pida)
# =============================================================

$ErrorActionPreference = "Stop"

# --- Configuración (edita si quieres otro nombre) ---
$GitHubUser = "alfonsfdez-beep"
$RepoName   = "farmapricing-app"
$RepoDesc   = "Centro de decisiones de pricing y surtido para parafarmacia"

# --- Pedir el PAT (no lo pongas en el script) ---
$PAT = Read-Host -Prompt "Pega tu PAT de GitHub" -AsSecureString
$PAT_Plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($PAT)
)

# --- 1. Crear el repo (privado) ---
Write-Host "`n[1/4] Creando repo $GitHubUser/$RepoName en GitHub..." -ForegroundColor Cyan
$body = @{
    name        = $RepoName
    description = $RepoDesc
    private     = $true
    auto_init   = $false
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Method Post `
        -Uri "https://api.github.com/user/repos" `
        -Headers @{
            Authorization = "token $PAT_Plain"
            Accept        = "application/vnd.github+json"
        } `
        -Body $body `
        -ContentType "application/json"
    Write-Host "    Repo creado: $($response.html_url)" -ForegroundColor Green
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 422) {
        Write-Host "    El repo ya existe. Continuando..." -ForegroundColor Yellow
    } else {
        Write-Host "    ERROR creando el repo: $_" -ForegroundColor Red
        exit 1
    }
}

# --- 2. Inicializar git en la carpeta actual ---
Write-Host "`n[2/4] Inicializando git en la carpeta actual..." -ForegroundColor Cyan
if (-not (Test-Path ".git")) {
    git init | Out-Null
    git branch -M main
}

# Asegurarse de tener identidad configurada
$gitEmail = git config user.email 2>$null
if (-not $gitEmail) {
    git config user.email "alfonsfdez@gmail.com"
    git config user.name  $GitHubUser
}

# --- 3. Primer commit ---
Write-Host "`n[3/4] Haciendo commit..." -ForegroundColor Cyan
git add .
git commit -m "Initial commit: app Streamlit de pricing y surtido" --allow-empty | Out-Null

# --- 4. Push usando el PAT en la URL del remote ---
Write-Host "`n[4/4] Push a GitHub..." -ForegroundColor Cyan
$remoteUrlAuth = "https://${GitHubUser}:${PAT_Plain}@github.com/$GitHubUser/$RepoName.git"
$remoteUrlClean = "https://github.com/$GitHubUser/$RepoName.git"

# Forzar reset del remote por si quedó de un intento anterior
try { git remote remove origin 2>&1 | Out-Null } catch {}
$LASTEXITCODE = 0  # ignorar exit code si origin no existía
git remote add origin $remoteUrlAuth
git push -u origin main

# Quitar el PAT de la URL del remote para no dejarlo guardado en .git/config
git remote set-url origin $remoteUrlClean

Write-Host "`nListo!" -ForegroundColor Green
Write-Host "Repo: https://github.com/$GitHubUser/$RepoName" -ForegroundColor Green
Write-Host "`nSiguiente paso: entra en https://share.streamlit.io" -ForegroundColor Cyan
Write-Host "  - New app -> selecciona el repo $RepoName" -ForegroundColor Cyan
Write-Host "  - Main file: streamlit_app.py" -ForegroundColor Cyan
Write-Host "  - Advanced settings -> Secrets: pega el TOML generado por genera_secrets_toml.py" -ForegroundColor Cyan
Write-Host "`nIMPORTANTE: revoca el PAT en GitHub cuando termines (lo expusiste en chat)." -ForegroundColor Yellow
