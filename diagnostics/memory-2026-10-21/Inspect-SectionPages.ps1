# Only query page metadata; do not read/touch target contents or page them into RAM.
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class SectionPageCounts {
 public int PID,Error; public string Base; public long Bytes,ValidBytes,ValidShareableBytes,InvalidResidentBytes,InvalidPagefileBytes,InvalidOtherBytes,InvalidModifiedBytes;
}
public static class SectionPagesReadOnly {
 [DllImport("kernel32.dll",SetLastError=true)] static extern IntPtr OpenProcess(uint access,bool inherit,int pid);
 [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);
 [DllImport("psapi.dll",SetLastError=true)] static extern bool QueryWorkingSetEx(IntPtr h,IntPtr buffer,int size);
 public static SectionPageCounts Count(int pid,long address,long bytes){
  var r=new SectionPageCounts{PID=pid,Base="0x"+address.ToString("X"),Bytes=bytes};IntPtr h=OpenProcess(0x410,false,pid);
  if(h==IntPtr.Zero){r.Error=Marshal.GetLastWin32Error();return r;}
  IntPtr buf=Marshal.AllocHGlobal(65536*16);
  try{for(long offset=0;offset<bytes;){int count=(int)Math.Min(65536,(bytes-offset)/4096);if(count==0)break;
   for(int i=0;i<count;i++){Marshal.WriteInt64(buf,i*16,address+offset+i*4096);Marshal.WriteInt64(buf,i*16+8,0);}
   if(!QueryWorkingSetEx(h,buf,count*16)){r.Error=Marshal.GetLastWin32Error();return r;}
   for(int i=0;i<count;i++){ulong flags=(ulong)Marshal.ReadInt64(buf,i*16+8);
    if((flags&1)!=0){r.ValidBytes+=4096;if((flags&0x8000)!=0)r.ValidShareableBytes+=4096;}
    else{int location=(int)((flags>>22)&3);if(location==1)r.InvalidResidentBytes+=4096;else if(location==2)r.InvalidPagefileBytes+=4096;else r.InvalidOtherBytes+=4096;if((flags&(1UL<<27))!=0)r.InvalidModifiedBytes+=4096;}
   }offset+=count*4096L;
  }return r;}finally{Marshal.FreeHGlobal(buf);CloseHandle(h);}
 }
}
'@
$maps=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'admin-shared-memory-maps.json') -Raw|ConvertFrom-Json
$candidates=@(foreach($p in $maps|Where-Object Name -eq 'postgres'){foreach($r in $p.Regions|Where-Object {$_.Type -eq 'Mapped' -and !$_.File -and $_.RegionBytes -ge 100MB}){[pscustomobject]@{PID=$p.PID;Base=$r.AllocationBase;Bytes=$r.RegionBytes}}})
# One mapped view per distinct allocation/size; do not add duplicate child views.
$counts=@(foreach($group in $candidates|Group-Object Base,Bytes){$c=$group.Group[0];[SectionPagesReadOnly]::Count($c.PID,[Convert]::ToInt64($c.Base.Substring(2),16),$c.Bytes)})
[pscustomobject]@{Timestamp=(Get-Date).ToString('o');Method='QueryWorkingSetEx; invalid Location from phnt MEMORY_WORKING_SET_EX_BLOCK; no memory contents read';Sections=$counts}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $PSScriptRoot 'postgres-section-pages.json') -Encoding utf8
