$ErrorActionPreference = 'Continue'
$out = $PSScriptRoot
function Save-Data($Name, $Data) { ConvertTo-Json -InputObject $Data -Depth 8 | Set-Content -LiteralPath (Join-Path $out "$Name.json") -Encoding utf8 }
function Exe-Only([string]$s) {
    if ($s -match '^\s*"([^"]+)"') { return $Matches[1] }
    if ($s -match '^\s*(.+?\.(exe|com|cmd|bat|ps1|vbs))(?=\s|$)') { return $Matches[1] }
    if ($s -match '^\s*(\S+)') { return $Matches[1] }
    return ''
}
$os = Get-CimInstance Win32_OperatingSystem
Save-Data 'system' ([ordered]@{
    Timestamp=(Get-Date).ToString('o')
    Elevated=([Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    OS=$os | Select-Object Caption,Version,BuildNumber,LastBootUpTime,TotalVisibleMemorySize,FreePhysicalMemory,TotalVirtualMemorySize,FreeVirtualMemory
    Computer=Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory,AutomaticManagedPagefile,HypervisorPresent
    RAM=@(Get-CimInstance Win32_PhysicalMemory | Select-Object Capacity,Speed,ConfiguredClockSpeed,Manufacturer)
    CPU=Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors
    GPU=@(Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,AdapterRAM)
    PageFiles=@(Get-CimInstance Win32_PageFileUsage | Select-Object Name,AllocatedBaseSize,CurrentUsage,PeakUsage)
    PageFileSettings=@(Get-CimInstance Win32_PageFileSetting | Select-Object Name,InitialSize,MaximumSize)
    Disks=@(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Select-Object DeviceID,Size,FreeSpace)
})
$perf = Get-CimInstance Win32_PerfFormattedData_PerfProc_Process | Where-Object {$_.Name -notin @('_Total','Idle')}
Save-Data 'processes' @($perf | Select-Object Name,IDProcess,CreatingProcessID,WorkingSet,WorkingSetPrivate,PrivateBytes,VirtualBytes,PageFileBytes,PoolNonpagedBytes,PoolPagedBytes,HandleCount,ThreadCount,PageFaultsPersec,PercentProcessorTime)
$procs = Get-CimInstance Win32_Process
Save-Data 'process-metadata' @($procs | Select-Object Name,ProcessId,ParentProcessId,ExecutablePath,CreationDate)
$java = foreach ($p in $procs | Where-Object {$_.Name -match '^(javaw?|java.*|Minecraft.*)\.exe$'}) {
    [pscustomobject]@{Name=$p.Name;PID=$p.ProcessId;MemoryFlags=@([regex]::Matches($p.CommandLine,'(?i)(?:-Xm[xs]\s*\d+[kmg]?|-XX:(?:MaxRAMPercentage|InitialRAMPercentage|MaxDirectMemorySize|NativeMemoryTracking)=[\w.]+|-XX:[+-](?:UseG1GC|UseZGC|AlwaysPreTouch))') | ForEach-Object {$_.Value})}
}
Save-Data 'java-memory-flags' @($java)
$services=Get-CimInstance Win32_Service
Save-Data 'services' @($services | Select-Object Name,DisplayName,State,StartMode,ProcessId,@{n='Executable';e={Exe-Only $_.PathName}})
Save-Data 'drivers' @(Get-CimInstance Win32_SystemDriver | Select-Object Name,DisplayName,State,StartMode,ServiceType,PathName)
Save-Data 'startup' @(Get-CimInstance Win32_StartupCommand | Select-Object Name,Location,@{n='Executable';e={Exe-Only $_.Command}})
$uninstallPaths=@('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*','HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*')
Save-Data 'installed-relevant' @(Get-ItemProperty -Path $uninstallPaths -ErrorAction SilentlyContinue | Where-Object {$_.DisplayName -match 'WSL|Linux|Docker|Hyper-V|BlueStacks|Ollama|NVIDIA|Intel.*(Graphics|Wireless)|VirtualBox|VMware|MySQL|SQL Server|Java|Minecraft|Forge|WARP|Amnezia|ASCON|АСКОН|KOMPAS|КОМПАС'} | Select-Object DisplayName,DisplayVersion,Publisher,InstallDate)
Save-Data 'optional-features' @(Get-CimInstance Win32_OptionalFeature | Where-Object {$_.Name -match 'Hyper-V|VirtualMachine|Subsystem-Linux|Containers|Hypervisor'} | Select-Object Name,InstallState)
Save-Data 'scheduled-startup' @(Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object {$_.State -ne 'Disabled' -and (($_.Triggers.CimClass.CimClassName -join ' ') -match 'Boot|Logon' -or $_.TaskName -match 'Docker|BlueStacks|Ollama|MySQL|ASCON|АСКОН|Amnezia')} | ForEach-Object {
    [pscustomobject]@{Name=$_.TaskName;Path=$_.TaskPath;State=[string]$_.State;Triggers=@($_.Triggers.CimClass.CimClassName);Executables=@($_.Actions | ForEach-Object {Exe-Only $_.Execute})}
})
$regStarts = foreach ($regPath in @('HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run','HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder','HKLM:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run','HKLM:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run32')) {
    $props=Get-ItemProperty -LiteralPath $regPath -ErrorAction SilentlyContinue
    foreach ($p in $props.PSObject.Properties | Where-Object {$_.Name -notmatch '^PS'}) { [pscustomobject]@{Location=$regPath;Name=$p.Name;StateByte=if($p.Value -is [byte[]]){$p.Value[0]}else{$null}} }
}
Save-Data 'startup-approved' @($regStarts)
$wslExe=Get-Command wsl.exe -ErrorAction SilentlyContinue
if ($wslExe) { (& $wslExe.Source --list --verbose 2>&1 | Out-String) -replace "`0",'' | Set-Content -LiteralPath (Join-Path $out 'wsl-list.txt') -Encoding utf8 }
$wslConfig=Join-Path $env:USERPROFILE '.wslconfig'
if (Test-Path -LiteralPath $wslConfig) { Save-Data 'wsl-resource-limits' @(Get-Content -LiteralPath $wslConfig | Where-Object {$_ -match '^\s*(\[.*\]|memory\s*=|processors\s*=|swap\s*=|autoMemoryReclaim\s*=|pageReporting\s*=)'}) }
$nvidia=Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue
if ($nvidia) { & $nvidia.Source --query-gpu=name,driver_version,memory.total,memory.used,utilization.gpu,temperature.gpu --format=csv,noheader | Set-Content -LiteralPath (Join-Path $out 'nvidia-gpu.txt') -Encoding utf8 }
try { Save-Data 'ollama-loaded-models' (Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/ps' -TimeoutSec 3 | Select-Object models) } catch { Save-Data 'ollama-api-status' @{Available=$false;ExceptionType=$_.Exception.GetType().Name} }
$since=(Get-Date).AddDays(-7)
Save-Data 'resource-exhaustion-events' @(Get-WinEvent -FilterHashtable @{LogName='System';ProviderName='Microsoft-Windows-Resource-Exhaustion-Detector';Id=2004;StartTime=$since} -ErrorAction SilentlyContinue | ForEach-Object {
    [xml]$xml=$_.ToXml()
    [pscustomobject]@{TimeCreated=$_.TimeCreated;ID=$_.Id;EventDataXml=$xml.Event.EventData.InnerXml;UserDataXml=$xml.Event.UserData.InnerXml}
})
$samples=for($i=0;$i -lt 13;$i++) {
    $m=Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
    $disk=Get-CimInstance Win32_PerfFormattedData_PerfDisk_PhysicalDisk | Where-Object {$_.Name -eq '_Total'}
    [pscustomobject]@{Timestamp=(Get-Date).ToString('o');Memory=$m | Select-Object AvailableBytes,CommittedBytes,CommitLimit,PoolNonpagedBytes,PoolPagedBytes,PoolPagedResidentBytes,SystemCacheResidentBytes,StandbyCacheCoreBytes,StandbyCacheNormalPriorityBytes,StandbyCacheReserveBytes,FreeAndZeroPageListBytes,ModifiedPageListBytes,PagesPersec,PagesInputPersec,PagesOutputPersec,PageReadsPersec,PageWritesPersec,PageFaultsPersec,TransitionFaultsPersec;Disk=$disk | Select-Object DiskReadBytesPersec,DiskWriteBytesPersec,AvgDisksecPerRead,AvgDisksecPerWrite,CurrentDiskQueueLength}
    if ($i -lt 12) { Start-Sleep -Seconds 5 }
}
Save-Data 'samples' @($samples)
Save-Data 'processes-end' @(Get-CimInstance Win32_PerfFormattedData_PerfProc_Process | Where-Object {$_.Name -notin @('_Total','Idle')} | Select-Object Name,IDProcess,WorkingSet,WorkingSetPrivate,PrivateBytes,HandleCount,ThreadCount)
'Collection complete: '+$out
