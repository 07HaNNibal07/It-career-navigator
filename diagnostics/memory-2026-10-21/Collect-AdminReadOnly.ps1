# Requires administrator ONLY to query protected process metadata and kernel pool tags.
# No services, configurations, files, registry values or page-file settings are changed.
$ErrorActionPreference='Continue'
$isAdmin=([Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (!$isAdmin) { throw 'Run this diagnostic script as administrator.' }
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Collections.Generic;
public static class AdminMemoryReadOnly {
 [StructLayout(LayoutKind.Sequential)] struct LUID {public uint Low;public int High;}
 [StructLayout(LayoutKind.Sequential)] struct TOKEN_PRIVILEGES {public uint Count;public LUID Luid;public uint Attributes;}
 [DllImport("kernel32.dll")] static extern IntPtr GetCurrentProcess();
 [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);
 [DllImport("advapi32.dll",SetLastError=true)] static extern bool OpenProcessToken(IntPtr p,uint access,out IntPtr token);
 [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool LookupPrivilegeValue(string sys,string name,out LUID luid);
 [DllImport("advapi32.dll",SetLastError=true)] static extern bool AdjustTokenPrivileges(IntPtr token,bool disable,ref TOKEN_PRIVILEGES state,uint size,IntPtr prev,IntPtr returned);
 [DllImport("ntdll.dll")] static extern int NtQuerySystemInformation(int cls,IntPtr buffer,int size,out int required);
 public static bool EnableDiagnosticPrivilege(string name){IntPtr t;if(!OpenProcessToken(GetCurrentProcess(),0x28,out t))return false;try{LUID id;if(!LookupPrivilegeValue(null,name,out id))return false;var s=new TOKEN_PRIVILEGES{Count=1,Luid=id,Attributes=2};return AdjustTokenPrivileges(t,false,ref s,0,IntPtr.Zero,IntPtr.Zero)&&Marshal.GetLastWin32Error()==0;}finally{CloseHandle(t);}}
 public class PoolTag { public string Tag;public uint PagedAllocs,PagedFrees,NonpagedAllocs,NonpagedFrees;public long PagedBytes,NonpagedBytes; }
 public class PoolResult {public string Status;public PoolTag[] Tags;}
 public static PoolResult Pools(){
  IntPtr buf=IntPtr.Zero;try{int len=1024*1024,needed,status;
   while(true){if(buf!=IntPtr.Zero)Marshal.FreeHGlobal(buf);buf=Marshal.AllocHGlobal(len);status=NtQuerySystemInformation(22,buf,len,out needed);if(status==0)break;if((uint)status!=0xC0000004)return new PoolResult{Status="0x"+((uint)status).ToString("X8")};len=Math.Max(len*2,needed+65536);if(len>128*1024*1024)return new PoolResult{Status="size limit"};}
   int count=Marshal.ReadInt32(buf);var rows=new List<PoolTag>();
   for(int i=0;i<count;i++){IntPtr p=IntPtr.Add(buf,8+i*40);byte[] tag=new byte[4];Marshal.Copy(p,tag,0,4);string name="";foreach(byte b in tag)name+=(b>=32&&b<127)?(char)b:'?';rows.Add(new PoolTag{Tag=name,PagedAllocs=(uint)Marshal.ReadInt32(p,4),PagedFrees=(uint)Marshal.ReadInt32(p,8),PagedBytes=Marshal.ReadInt64(p,16),NonpagedAllocs=(uint)Marshal.ReadInt32(p,24),NonpagedFrees=(uint)Marshal.ReadInt32(p,28),NonpagedBytes=Marshal.ReadInt64(p,32)});}
   return new PoolResult{Status="OK",Tags=rows.ToArray()};
  }finally{if(buf!=IntPtr.Zero)Marshal.FreeHGlobal(buf);}
 }
}
'@
$privileges=[pscustomobject]@{Timestamp=(Get-Date).ToString('o');Debug=[AdminMemoryReadOnly]::EnableDiagnosticPrivilege('SeDebugPrivilege');Profile=[AdminMemoryReadOnly]::EnableDiagnosticPrivilege('SeProfileSingleProcessPrivilege')}
$privileges | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'admin-status.json') -Encoding utf8
[AdminMemoryReadOnly]::Pools() | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'pool-tags.json') -Encoding utf8
& (Join-Path $PSScriptRoot 'Inspect-SharedMemory.ps1') -OutputName 'admin-shared-memory-maps.json'
& (Join-Path $PSScriptRoot 'Inspect-SectionPages.ps1')
Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'postgres|pg_ctl|mysqld|dwm|nvcontainer|NVDisplay'} | Select-Object Name,ProcessId,ParentProcessId,ExecutablePath,@{n='MemoryOverrides';e={@([regex]::Matches($_.CommandLine,'(?i)(?:shared_buffers|max_connections|work_mem|maintenance_work_mem|huge_pages|shared_memory_type)\s*=\s*[\w.]+')|ForEach-Object {$_.Value})}} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'admin-process-metadata.json') -Encoding utf8
'Completed: '+(Get-Date).ToString('o') | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'admin-complete.txt') -Encoding utf8
