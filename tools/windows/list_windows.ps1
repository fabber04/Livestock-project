Get-Process | ForEach-Object {
  $title = $_.MainWindowTitle
  if ($title) {
    Write-Output ("{0}`t{1}`t{2}" -f $_.Id, $_.ProcessName, $title)
  }
}
