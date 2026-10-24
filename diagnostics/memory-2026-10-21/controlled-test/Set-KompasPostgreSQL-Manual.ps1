# Explicitly requested by the user: change ONLY KOMPAS PostgreSQL startup to Manual.
$ErrorActionPreference='Stop'
$output=Join-Path $PSScriptRoot 'startup-mode-change.json'
try {
 $names=@('PostgreSQL','postgresql-x64-16','postgresql-x64-17','MySQL80','PolynomMdmApiSvc')
 $before=@(Get-CimInstance Win32_Service|Where-Object {$_.Name -in $names}|Select-Object Name,State,StartMode,ProcessId)
 $target=Get-CimInstance Win32_Service -Filter "Name='PostgreSQL'"
 $expectedExe='C:\Program Files\ASCON\KOMPAS-3D v25 Study\Libs\PolynomLib\Templates\LocalBase\bin\pg_ctl.exe'
 $expectedData='C:\Program Files\ASCON\KOMPAS-3D v25 Study\Libs\PolynomLib\Templates\LocalBase\data'
 if($target.PathName -notmatch '^"([^"]+)"' -or $Matches[1] -ne $expectedExe){throw 'KOMPAS executable mismatch. No change made.'}
 if($target.PathName -notmatch '(?i)(?:^|\s)-D\s+"([^"]+)"' -or $Matches[1] -ne $expectedData){throw 'KOMPAS data directory mismatch. No change made.'}
 Set-Service -Name 'PostgreSQL' -StartupType Manual
 $after=@(Get-CimInstance Win32_Service|Where-Object {$_.Name -in $names}|Select-Object Name,State,StartMode,ProcessId)
 $newTarget=$after|Where-Object Name -eq PostgreSQL
 $controls=@(foreach($old in $before|Where-Object Name -ne PostgreSQL){$new=$after|Where-Object Name -eq $old.Name;[pscustomobject]@{Name=$old.Name;SamePID=($old.ProcessId -eq $new.ProcessId);SameState=($old.State -eq $new.State);SameStartMode=($old.StartMode -eq $new.StartMode)}})
 [pscustomobject]@{Timestamp=(Get-Date).ToString('o');Succeeded=($newTarget.StartMode -eq 'Manual');ExactService='PostgreSQL';Executable=$expectedExe;Before=$before;After=$after;OtherServices=$controls}|ConvertTo-Json -Depth 7|Set-Content -LiteralPath $output -Encoding utf8
}catch{
 [pscustomobject]@{Timestamp=(Get-Date).ToString('o');Succeeded=$false;Message=$_.Exception.Message}|ConvertTo-Json|Set-Content -LiteralPath $output -Encoding utf8
 exit 1
}
