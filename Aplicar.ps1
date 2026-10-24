param([Parameter(Mandatory=$true)][string]$Proyecto)
$ErrorActionPreference='Stop'
$raizProyecto=(Resolve-Path -LiteralPath $Proyecto).Path
$rutaApi=Join-Path $raizProyecto 'backend/api'
$rutaApp=Join-Path $rutaApi 'app.py'
$rutaCors=Join-Path $rutaApi 'cors.py'
if (-not (Test-Path -LiteralPath $rutaApp -PathType Leaf)) { throw 'La carpeta indicada no contiene backend/api/app.py.' }
$hashEsperado=(Get-Content -LiteralPath (Join-Path $PSScriptRoot 'original-app.sha256') -Raw).Trim()
$hashActual=(Get-FileHash -LiteralPath $rutaApp -Algorithm SHA256).Hash
if ($hashActual -ne $hashEsperado) { throw 'app.py cambió desde la revisión. No se reemplazó ningún archivo. Revisa CAMBIOS.patch sobre la versión nueva.' }
if (Test-Path -LiteralPath $rutaCors) { throw 'Ya existe cors.py. Revisa el archivo antes de aplicar esta corrección; no se reemplazó ningún archivo.' }
$sufijoCopia=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
Copy-Item -LiteralPath $rutaApp -Destination "$rutaApp.antes-cors-$sufijoCopia.bak"
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'backend/api/cors.py') -Destination $rutaCors
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'backend/api/app.py') -Destination $rutaApp
Write-Host 'Corrección aplicada a backend/api/app.py y cors.py. Se guardó una copia del app.py anterior.'
Write-Host 'Falta reiniciar el proceso del backend con su configuración y entorno habituales. No se modificó la base de datos ni se reinició el túnel.'
