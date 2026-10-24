function Save-ControlJson($Name,$Data) { ConvertTo-Json -InputObject $Data -Depth 8 | Set-Content -LiteralPath (Join-Path $PSScriptRoot $Name) -Encoding utf8 }
function Measure-ControlMemory {
 $os=Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
 $m=Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory -ErrorAction Stop
 [pscustomobject]@{Timestamp=(Get-Date).ToString('o');VisiblePhysicalBytes=[long]$os.TotalVisibleMemorySize*1024;AvailableBytes=[long]$m.AvailableBytes;UsedPhysicalBytes=([long]$os.TotalVisibleMemorySize*1024-[long]$m.AvailableBytes);CommittedBytes=[long]$m.CommittedBytes;CommitLimit=[long]$m.CommitLimit;NonpagedBytes=[long]$m.PoolNonpagedBytes;PagedResidentBytes=[long]$m.PoolPagedResidentBytes;PagesInputPersec=$m.PagesInputPersec;PagesOutputPersec=$m.PagesOutputPersec}
}
function Get-ControlServices {
 @(Get-CimInstance Win32_Service -ErrorAction Stop | Where-Object {$_.Name -in @('PostgreSQL','postgresql-x64-16','postgresql-x64-17','MySQL80','PolynomMdmApiSvc')} | Select-Object Name,State,StartMode,ProcessId)
}
function Test-KompasDatabaseIdle {
 $s=Get-CimInstance Win32_Service -Filter "Name='PostgreSQL'" -ErrorAction Stop
 $expectedExe='C:\Program Files\ASCON\KOMPAS-3D v25 Study\Libs\PolynomLib\Templates\LocalBase\bin\pg_ctl.exe'
 $expectedData='C:\Program Files\ASCON\KOMPAS-3D v25 Study\Libs\PolynomLib\Templates\LocalBase\data'
 if($s.PathName -notmatch '^"([^"]+)"' -or $Matches[1] -ne $expectedExe){throw 'Target service executable does not match KOMPAS. No stop allowed.'}
 if($s.PathName -notmatch '(?i)(?:^|\s)-D\s+"([^"]+)"' -or $Matches[1] -ne $expectedData){throw 'Target service data directory does not match KOMPAS. No stop allowed.'}
 if($s.State -ne 'Running'){throw 'Target service is not Running.'}
 $apps=@(Get-Process -ErrorAction Stop|Where-Object {$_.ProcessName -match '^kompas(?:\.exe)?$|^kOMPAS|^Polynom.*Client|^Polynom.*Browser'})
 if($apps.Count){throw 'KOMPAS/POLYNOM client application detected. No stop allowed.'}
 if(@((Get-Service -Name PostgreSQL -ErrorAction Stop).DependentServices|Where-Object Status -ne Stopped).Count){throw 'Running dependent service detected. No stop allowed.'}
 $env:PGCONNECT_TIMEOUT='3'
 $psql=Join-Path (Split-Path $expectedExe) 'psql.exe'
 # One read-only statement: output only identity and counts, never query texts or credentials.
 $sql="SELECT current_setting('data_directory') || '|' || count(*) FILTER (WHERE pid <> pg_backend_pid() AND state IS NOT NULL) || '|' || count(*) FILTER (WHERE pid <> pg_backend_pid() AND state = 'active') FROM pg_stat_activity;"
 $result=@(& $psql -X -w -A -t -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5433 -U postgres -d postgres -c $sql 2>&1|ForEach-Object {[string]$_})
 if($LASTEXITCODE -ne 0){throw 'Could not verify database client counts. No stop allowed.'}
 $value=($result|Where-Object {$_ -match '\|\d+\|\d+$'}|Select-Object -Last 1)
 if(!$value){throw 'Unexpected database verification response. No stop allowed.'}
 $fields=$value -split '\|'
 if(($fields[0] -replace '/','\') -ne $expectedData){throw 'Connected database is not the KOMPAS cluster. No stop allowed.'}
 if([int]$fields[1] -ne 0 -or [int]$fields[2] -ne 0){throw 'Other database clients detected. No stop allowed.'}
 [pscustomobject]@{Timestamp=(Get-Date).ToString('o');Name=$s.Name;ServicePID=$s.ProcessId;Executable=$expectedExe;DataDirectory=$expectedData;OtherClientSessions=[int]$fields[1];ActiveOtherClientSessions=[int]$fields[2];KompasClientProcesses=$apps.Count;PolynomServiceState=(Get-Service -Name PolynomMdmApiSvc -ErrorAction Stop).Status.ToString()}
}
