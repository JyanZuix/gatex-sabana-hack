param(
    [string]$Api='https://colleges-employees-fighter-allen.trycloudflare.com',
    [string]$Origen='https://shimmering-mousse-135327.netlify.app'
)
$ErrorActionPreference='Stop'
function ProbarRespuesta([string]$Metodo,[string]$Ruta,[hashtable]$Cabeceras) {
    try {
        $r=Invoke-WebRequest -Uri ($Api.TrimEnd('/')+$Ruta) -Method $Metodo -Headers $Cabeceras -TimeoutSec 20
        $permitido=[string]$r.Headers['Access-Control-Allow-Origin']
        [pscustomobject]@{Metodo=$Metodo;Ruta=$Ruta;HTTP=[int]$r.StatusCode;OrigenSolicitado=$Origen;AllowOrigin=$permitido;CORSValido=($permitido -eq '*' -or $permitido -eq $Origen);AllowMethods=[string]$r.Headers['Access-Control-Allow-Methods'];AllowHeaders=[string]$r.Headers['Access-Control-Allow-Headers']} | Format-List
    } catch { Write-Host "$Metodo $Ruta falló: $($_.Exception.Message)" }
}
ProbarRespuesta 'GET' '/salud' @{Origin=$Origen}
ProbarRespuesta 'OPTIONS' '/solicitudes/evaluar' @{Origin=$Origen;'Access-Control-Request-Method'='POST';'Access-Control-Request-Headers'='content-type'}
# Solo lectura y preflight. No se envía una evaluación ni se guarda una decisión.
