# Read-only address-space metadata. No process memory contents are read.
param([string]$OutputName='shared-memory-maps.json')
$ErrorActionPreference='Continue'
Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;
public class RegionMemory {
 public string AllocationBase, Type, File; public long RegionBytes, ResidentBytes, ShareableResidentBytes, SharedResidentBytes, PrivateResidentBytes;
}
public class ProcessMemoryMap {
 public int PID, Error; public long ResidentBytes, ShareableResidentBytes, PrivateResidentBytes; public RegionMemory[] Regions;
}
public static class MemoryMetadata {
 [StructLayout(LayoutKind.Sequential)] struct MBI {public IntPtr BaseAddress,AllocationBase; public uint AllocationProtect; public ushort PartitionId; public UIntPtr RegionSize; public uint State,Protect,Type;}
 [DllImport("kernel32.dll",SetLastError=true)] static extern IntPtr OpenProcess(uint access,bool inherit,int pid);
 [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);
 [DllImport("kernel32.dll",SetLastError=true)] static extern UIntPtr VirtualQueryEx(IntPtr h,IntPtr address,out MBI info,UIntPtr length);
 [DllImport("psapi.dll",SetLastError=true)] static extern bool QueryWorkingSet(IntPtr h,IntPtr buffer,int length);
 [DllImport("psapi.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern uint GetMappedFileName(IntPtr h,IntPtr address,StringBuilder name,int length);
 public static ProcessMemoryMap Inspect(int pid) {
  var result=new ProcessMemoryMap{PID=pid};
  var h=OpenProcess(0x410,false,pid);
  if(h==IntPtr.Zero){result.Error=Marshal.GetLastWin32Error();return result;}
  IntPtr buffer=IntPtr.Zero;
  try {
   int length=1024*1024; bool ok=false;
   for(int attempt=0;attempt<9;attempt++){
    if(buffer!=IntPtr.Zero)Marshal.FreeHGlobal(buffer);
    buffer=Marshal.AllocHGlobal(length);
    if(QueryWorkingSet(h,buffer,length)){ok=true;break;}
    int err=Marshal.GetLastWin32Error(); if(err!=24 && err!=122){result.Error=err;return result;}
    length*=2;
   }
   if(!ok){result.Error=Marshal.GetLastWin32Error();return result;}
   long count=Marshal.ReadInt64(buffer);
   var regions=new Dictionary<long,RegionMemory>();
   var mbiCache=new SortedList<long,MBI>();
   MBI current=new MBI(); long currentStart=-1,currentEnd=-1;
   for(long i=0;i<count;i++){
    ulong entry=(ulong)Marshal.ReadInt64(buffer,checked((int)((i+1)*8)));
    long addr=(long)(entry & ~0xfffUL);
    if(addr<currentStart || addr>=currentEnd){
     if(VirtualQueryEx(h,new IntPtr(addr),out current,(UIntPtr)Marshal.SizeOf<MBI>())==UIntPtr.Zero)continue;
     currentStart=current.BaseAddress.ToInt64();currentEnd=currentStart+(long)current.RegionSize.ToUInt64();
    }
    long allocation=current.AllocationBase.ToInt64();
    RegionMemory r;
    if(!regions.TryGetValue(allocation,out r)){
     string type=current.Type==0x40000 ? "Mapped" : current.Type==0x1000000 ? "Image" : current.Type==0x20000 ? "Private" : "Other";
     var sb=new StringBuilder(2048);string file="";
     if(current.Type==0x40000 || current.Type==0x1000000){if(GetMappedFileName(h,new IntPtr(addr),sb,sb.Capacity)>0)file=sb.ToString();}
     r=new RegionMemory{AllocationBase="0x"+allocation.ToString("X"),Type=type,File=file};regions.Add(allocation,r);
    }
    bool shared=(entry & 0x100UL)!=0;int shareCount=(int)((entry>>5)&7);
    r.ResidentBytes+=4096; result.ResidentBytes+=4096;
    if(shared){r.ShareableResidentBytes+=4096;result.ShareableResidentBytes+=4096;if(shareCount>1)r.SharedResidentBytes+=4096;}
    else{r.PrivateResidentBytes+=4096;result.PrivateResidentBytes+=4096;}
   }
   // Obtain total committed virtual size per allocation without touching page data.
   long cursor=0;MBI info;
   while(VirtualQueryEx(h,new IntPtr(cursor),out info,(UIntPtr)Marshal.SizeOf<MBI>())!=UIntPtr.Zero){
    long size=(long)info.RegionSize.ToUInt64(); long next=info.BaseAddress.ToInt64()+size;
    RegionMemory r;if(info.State==0x1000 && regions.TryGetValue(info.AllocationBase.ToInt64(),out r))r.RegionBytes+=size;
    if(next<=cursor)break;cursor=next;
   }
   result.Regions=new List<RegionMemory>(regions.Values).ToArray();return result;
  }finally{if(buffer!=IntPtr.Zero)Marshal.FreeHGlobal(buffer);CloseHandle(h);}
 }
}
'@
$items=foreach($p in Get-Process | Where-Object {$_.Id -gt 4}) {
    $map=[MemoryMetadata]::Inspect($p.Id)
    [pscustomobject]@{Timestamp=(Get-Date).ToString('o');Name=$p.ProcessName;PID=$p.Id;Error=$map.Error;ResidentBytes=$map.ResidentBytes;ShareableResidentBytes=$map.ShareableResidentBytes;PrivateResidentBytes=$map.PrivateResidentBytes;Regions=@($map.Regions | Where-Object {$_.ResidentBytes -ge 4MB -or ($_.Type -eq 'Mapped' -and $_.ResidentBytes -ge 1MB)} | Sort-Object ResidentBytes -Descending)}
}
$items | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $PSScriptRoot $OutputName) -Encoding utf8
$items | Where-Object {$_.Error -eq 0} | Sort-Object ShareableResidentBytes -Descending | Select-Object -First 30 Name,PID,@{n='WS_MiB';e={[math]::Round($_.ResidentBytes/1MB,1)}},@{n='ShareableWS_MiB';e={[math]::Round($_.ShareableResidentBytes/1MB,1)}},@{n='AnonymousMappedResident_MiB';e={[math]::Round(($_.Regions | Where-Object {$_.Type -eq 'Mapped' -and !$_.File} | Measure-Object ResidentBytes -Sum).Sum/1MB,1)}} | Format-Table -AutoSize
'Inaccessible processes: '+@($items | Where-Object Error -ne 0).Count
