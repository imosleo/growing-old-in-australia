param([string]$prefix = "shot", [int]$wheel = 0, [int]$mx = 900, [int]$my = 600)
$sp = Join-Path $PSScriptRoot "out"
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices; using System.Text;
public class WS {
 [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f);
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
 [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, int data, UIntPtr extra);
 public delegate bool EP(IntPtr h, IntPtr l);
 [DllImport("user32.dll")] public static extern bool EnumWindows(EP e, IntPtr l);
 [StructLayout(LayoutKind.Sequential)] public struct R { public int L,T,Rt,B; }
}
"@
$pids = (Get-Process tabpublic -ErrorAction SilentlyContinue).Id
$list = New-Object System.Collections.ArrayList
[WS]::EnumWindows({ param($h,$l) $p=0; [WS]::GetWindowThreadProcessId($h,[ref]$p) | Out-Null; if ($pids -contains $p -and [WS]::IsWindowVisible($h)) { $sb=New-Object System.Text.StringBuilder 256; [WS]::GetWindowText($h,$sb,256)|Out-Null; $list.Add(@{h=$h;t=$sb.ToString()})|Out-Null }; $true }, [IntPtr]::Zero) | Out-Null
$i=0
foreach ($w in $list) {
  $r = New-Object WS+R; [WS]::GetWindowRect($w.h,[ref]$r)|Out-Null
  $wd=$r.Rt-$r.L; $ht=$r.B-$r.T
  if ($wd -le 50 -or $ht -le 50) { continue }
  if ($wheel -ne 0 -and $w.t -like 'Tableau Public -*') {
    [WS]::SetForegroundWindow($w.h) | Out-Null; Start-Sleep -Milliseconds 300
    [WS]::SetCursorPos($r.L + $mx, $r.T + $my) | Out-Null
    $n = [Math]::Abs($wheel); $d = if ($wheel -gt 0) { -120 } else { 120 }
    for ($k=0; $k -lt $n; $k++) { [WS]::mouse_event(0x0800, 0, 0, $d, [UIntPtr]::Zero); Start-Sleep -Milliseconds 60 }
    Start-Sleep -Milliseconds 900
  }
  "win $i : '$($w.t)' ${wd}x${ht}"
  $bmp = New-Object System.Drawing.Bitmap $wd,$ht
  $g=[System.Drawing.Graphics]::FromImage($bmp); $dc=$g.GetHdc()
  [WS]::PrintWindow($w.h,$dc,2)|Out-Null; $g.ReleaseHdc($dc); $g.Dispose()
  $bmp.Save("$sp\$prefix`_$i.png"); $bmp.Dispose()
  $i++
}
