param(
  [switch]$SkipExeBuild,
  [switch]$InstallTest
)

$ErrorActionPreference = "Stop"

$installerDir = $PSScriptRoot
$root = Split-Path -Parent (Split-Path -Parent $installerDir)
$wix = "$env:USERPROFILE\.dotnet\tools\wix.exe"
$version = "0.1.1"
$msiPath = Join-Path $root "dist\ASCOS-Pdf2-$version.msi"

Write-Output "Proje koku: $root"

# 0) Calisan uygulama varsa kapat (dosya kilidi)
Get-Process -Name Pdf2 -ErrorAction SilentlyContinue | Stop-Process -Force

# 1) PyInstaller derlemesi
if (-not $SkipExeBuild) {
  Write-Output "PyInstaller derleniyor..."
  & "$root\.venv\Scripts\pyinstaller.exe" "$root\packaging\pdf2.spec" `
    --noconfirm --distpath "$root\dist" --workpath "$root\build" `
    | Select-Object -Last 2
  if ($LASTEXITCODE -ne 0) { throw "PyInstaller basarisiz, kod: $LASTEXITCODE" }
}

if (-not (Test-Path "$root\dist\Pdf2\Pdf2.exe")) {
  throw "dist\Pdf2\Pdf2.exe bulunamadi; once derleme yapin"
}

# 2) Lisans RTF'ini uret
& "$root\.venv\Scripts\python.exe" "$installerDir\make_license_rtf.py" `
  "$installerDir\license\AGPL-NOTICE.txt" "$installerDir\license\AGPL-3.0.rtf"
if ($LASTEXITCODE -ne 0) { throw "Lisans RTF uretilemedi" }

# 3) MSI derle
Write-Output "MSI derleniyor (cab sikistirma uzun surebilir)..."
Push-Location $installerDir
try {
  & $wix build -arch x64 `
    -ext WixToolset.UI.wixext -ext WixToolset.Util.wixext `
    -culture tr-TR `
    -o $msiPath "Product.wxs"
  if ($LASTEXITCODE -ne 0) { throw "wix build basarisiz, kod: $LASTEXITCODE" }
} finally {
  Pop-Location
}

$sizeMb = [math]::Round((Get-Item $msiPath).Length / 1MB)
Write-Output "MSI olusturuldu: $msiPath ($sizeMb MB)"

# 4) Dogrulama: paket gecerliligi ve yonetici cikarimi
# ICE38/43/64/91: per-user (kullanici profili) kurulum icin Microsoft'un kati
# ICE kurallari; dosya KeyPath'i ve profildeki dizinler bu kapsamda kabul
# edilebilir. Diger tum ICE denetimleri calisir; ayrica gercek kurulum testi yapilir.
$validation = & $wix msi validate $msiPath `
  -sice ICE38 -sice ICE43 -sice ICE64 -sice ICE91 2>&1 | Out-String
if ($validation -match "(?im)\berror\b") {
  Write-Output $validation
  throw "MSI dogrulama hatalari var"
}
Write-Output "MSI dogrulama: basarili (per-user muafiyetleriyle)"

Remove-Item -Recurse -Force (Join-Path $env:TEMP "pdf2_msi_check") -ErrorAction SilentlyContinue

# 5) Sessiz kurulum / smoke / kaldirma testi (asil uctan uca dogrulama)
if ($InstallTest) {
  Write-Output "Sessiz kurulum testi..."
  $install = Start-Process msiexec.exe -ArgumentList @("/i", "`"$msiPath`"", "/qn") -Wait -PassThru
  if ($install.ExitCode -ne 0) { throw "Sessiz kurulum basarisiz: $($install.ExitCode)" }

  $exe = Join-Path $env:LOCALAPPDATA "Programs\ASCOS Pdf2\Pdf2.exe"
  if (-not (Test-Path $exe)) { throw "Kurulan exe bulunamadi: $exe" }
  $installedCount = (
    Get-ChildItem (Join-Path $env:LOCALAPPDATA "Programs\ASCOS Pdf2") -Recurse -File |
      Measure-Object
  ).Count
  Write-Output "Kurulum dogrulandi: Pdf2.exe + $installedCount dosya"

  $env:PDF2_SMOKE = "1"
  $env:QT_QPA_PLATFORM = "offscreen"
  $smoke = Start-Process $exe -Wait -PassThru
  Remove-Item Env:\PDF2_SMOKE
  Remove-Item Env:\QT_QPA_PLATFORM
  if ($smoke.ExitCode -ne 0) { throw "Kurulu uygulama smoke testi basarisiz: $($smoke.ExitCode)" }
  Write-Output "Kurulu uygulama smoke testi: cikis 0"

  Write-Output "Sessiz kaldirma testi..."
  $uninstall = Start-Process msiexec.exe -ArgumentList @("/x", "`"$msiPath`"", "/qn") -Wait -PassThru
  if ($uninstall.ExitCode -ne 0) { throw "Kaldirma basarisiz: $($uninstall.ExitCode)" }
  if (Test-Path (Join-Path $env:LOCALAPPDATA "Programs\ASCOS Pdf2")) {
    throw "Kaldirma sonrasi klasor kaldi"
  }
  Write-Output "Kurulum/kaldirma testi tamam"
}

Write-Output "BITTI"
