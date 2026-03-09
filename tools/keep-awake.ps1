# keep-awake.ps1
# Prevents Windows from sleeping while this script is running.
# Usage: powershell -ExecutionPolicy Bypass -File keep-awake.ps1
# Stop:  Press Ctrl+C or close the window to restore normal sleep behavior.

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public static class SleepPreventer {
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern uint SetThreadExecutionState(uint esFlags);

    private const uint ES_CONTINUOUS       = 0x80000000;
    private const uint ES_SYSTEM_REQUIRED  = 0x00000001;
    private const uint ES_DISPLAY_REQUIRED = 0x00000002;

    public static void PreventSleep() {
        SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED);
    }

    public static void AllowSleep() {
        SetThreadExecutionState(ES_CONTINUOUS);
    }
}
"@

try {
    [SleepPreventer]::PreventSleep()
    Write-Host ""
    Write-Host "=== Keep Awake ==="
    Write-Host "Your laptop will NOT sleep while this window is open."
    Write-Host "Press Ctrl+C or close this window to restore normal sleep behavior."
    Write-Host ""

    while ($true) {
        $timestamp = Get-Date -Format "HH:mm:ss"
        Write-Host "[$timestamp] System awake - sleep prevented"
        Start-Sleep -Seconds 60
        # Refresh the execution state each loop iteration
        [SleepPreventer]::PreventSleep()
    }
}
finally {
    [SleepPreventer]::AllowSleep()
    Write-Host ""
    Write-Host "Normal sleep behavior restored. You can close this window."
}
