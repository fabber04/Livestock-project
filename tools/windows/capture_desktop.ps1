Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Get-Process | ForEach-Object {
  $title = $_.MainWindowTitle
  if ($title) {
    Write-Output ("{0}`t{1}" -f $_.ProcessName, $title)
  }
}
$frames = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) "simulation\frames"
New-Item -ItemType Directory -Force $frames | Out-Null
$i = 0
foreach ($screen in [System.Windows.Forms.Screen]::AllScreens) {
  $bounds = $screen.Bounds
  $bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
  $graphics = [System.Drawing.Graphics]::FromImage($bmp)
  $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
  $path = Join-Path $frames "desktop_$i.png"
  $bmp.Save($path)
  Write-Output ("saved {0} {1}" -f $path, $bounds)
  $i++
}
