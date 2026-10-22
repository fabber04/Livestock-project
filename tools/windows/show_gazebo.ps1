Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
  [StructLayout(LayoutKind.Sequential)]
  public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int cmd);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr hWnd, IntPtr after, int x, int y, int cx, int cy, uint flags);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, IntPtr pid);
  [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool attach);
  [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
}
"@
Add-Type -AssemblyName System.Drawing
$found = $false
Get-Process | ForEach-Object {
  $title = $_.MainWindowTitle
  if ($title -like "*Gazebo*") {
    $found = $true
    $handle = $_.MainWindowHandle
    Write-Output ("title={0}" -f $title)
    $fg = [Win32]::GetForegroundWindow()
    $fgThread = [Win32]::GetWindowThreadProcessId($fg, [IntPtr]::Zero)
    $cur = [Win32]::GetCurrentThreadId()
    [Win32]::AttachThreadInput($cur, $fgThread, $true) | Out-Null
    [Win32]::ShowWindow($handle, 9) | Out-Null
    [Win32]::SetWindowPos($handle, [IntPtr](-1), 60, 40, 1200, 760, 0x0040) | Out-Null
    [Win32]::SetForegroundWindow($handle) | Out-Null
    [Win32]::AttachThreadInput($cur, $fgThread, $false) | Out-Null
    Start-Sleep -Seconds 1
    $rect = New-Object Win32+RECT
    [Win32]::GetWindowRect($handle, [ref]$rect) | Out-Null
    $width = $rect.Right - $rect.Left
    $height = $rect.Bottom - $rect.Top
    $bmp = New-Object System.Drawing.Bitmap $width, $height
    $graphics = [System.Drawing.Graphics]::FromImage($bmp)
    $hdc = $graphics.GetHdc()
    $ok = [Win32]::PrintWindow($handle, $hdc, 2)
    $graphics.ReleaseHdc($hdc)
    $frames = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) "simulation\frames"
    New-Item -ItemType Directory -Force $frames | Out-Null
    $path = Join-Path $frames "gazebo_window.png"
    $bmp.Save($path)
    Write-Output ("printwindow={0} size={1}x{2} saved={3}" -f $ok, $width, $height, $path)
  }
}
if (-not $found) { Write-Output "no gazebo window" }
