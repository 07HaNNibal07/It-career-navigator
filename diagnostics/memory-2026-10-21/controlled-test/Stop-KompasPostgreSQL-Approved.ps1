# Run ONLY after explicit user confirmation to stop service PostgreSQL belonging to KOMPAS.
# Only this exact service is stopped; no Force, process termination, configuration or startup edits.
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'Measure-ControlMemory.ps1')
try {
 if(!([Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'Administrator rights required to send a service stop request.'}
 $check=Test-KompasDatabaseIdle
 Save-ControlJson 'pre-stop-check.json' $check
 $servicesBefore=Get-ControlServices
 Save-ControlJson 'services-immediately-before.json' $servicesBefore
 $config=Join-Path $check.DataDirectory 'postgresql.conf'
 $configHash=(Get-FileHash -LiteralPath $config -Algorithm SHA256).Hash
 $samplesBefore=@(1..3|ForEach-Object {Measure-ControlMemory;Start-Sleep -Seconds 1})
 Save-ControlJson 'memory-immediately-before.json' $samplesBefore
 $started=(Get-Date).ToString('o')
 Stop-Service -Name 'PostgreSQL' -NoWait -ErrorAction Stop
 (Get-Service -Name 'PostgreSQL').WaitForStatus([System.ServiceProcess.ServiceControllerStatus]::Stopped,[TimeSpan]::FromSeconds(45))
 $stopped=(Get-Date).ToString('o')
 $samplesAfter=@(1..11|ForEach-Object {Measure-ControlMemory;if($_ -lt 11){Start-Sleep -Seconds 2}})
 Save-ControlJson 'memory-after-stop.json' $samplesAfter
 $servicesAfter=Get-ControlServices
 Save-ControlJson 'services-after-stop.json' $servicesAfter
 $unchanged=@(foreach($old in $servicesBefore|Where-Object Name -ne PostgreSQL){$new=$servicesAfter|Where-Object Name -eq $old.Name;[pscustomobject]@{Name=$old.Name;SamePID=($new.ProcessId -eq $old.ProcessId);SameState=($new.State -eq $old.State);SameStartMode=($new.StartMode -eq $old.StartMode)}})
 $targetAfter=$servicesAfter|Where-Object Name -eq PostgreSQL
 Save-ControlJson 'stop-result.json' ([pscustomobject]@{Succeeded=($targetAfter.State -eq 'Stopped');RequestedAt=$started;StoppedAt=$stopped;ExactService='PostgreSQL';TargetStartModeUnchanged=($targetAfter.StartMode -eq ($servicesBefore|Where-Object Name -eq PostgreSQL).StartMode);ConfigHashUnchanged=((Get-FileHash -LiteralPath $config -Algorithm SHA256).Hash -eq $configHash);OtherServices=$unchanged})
 # Fresh RAMMap instance captures a new physical-memory snapshot; no Empty actions are used.
 $ramMap=Start-Process -FilePath 'C:\Users\Ильгар\Desktop\RAMMap\RAMMap64.exe' -PassThru
 Save-ControlJson 'rammap-after-launch.json' ([pscustomobject]@{PID=$ramMap.Id;Timestamp=(Get-Date).ToString('o')})
} catch {
 Save-ControlJson 'stop-error.json' ([pscustomobject]@{Timestamp=(Get-Date).ToString('o');Message=$_.Exception.Message})
 exit 1
}
