#!/usr/bin/env python3
"""
Simple Signal Telemetry Wrapper
Provides high-performance, subprocess-free Windows system metrics gathering (CPU, RAM, Disk, GPU).
"""

import os
import sys
import time
import subprocess
import psutil
import ctypes
from ctypes import byref, Structure, Union
from ctypes.wintypes import DWORD, HANDLE

# Windows Performance Data Helper (PDH) Constants and Types
PDH_HQUERY = HANDLE
PDH_HCOUNTER = HANDLE
PDH_FMT_DOUBLE = 0x00000200

class PDH_FMT_COUNTERVALUE_DOUBLE(Structure):
    class _Value(Union):
        _fields_ = [
            ("longValue", ctypes.c_long),
            ("doubleValue", ctypes.c_double),
            ("largeValue", ctypes.c_int64),
            ("AnsiStringValue", ctypes.c_char_p),
            ("WideStringValue", ctypes.c_wchar_p)
        ]
    _anonymous_ = ("value",)
    _fields_ = [
        ("CStatus", DWORD),
        ("value", _Value)
    ]

def get_gpu_info_data_sync():
    """Retrieve graphics cards list using PyTorch backends and fallback WMI video controllers"""
    gpu_list = []
    
    # 1. PyTorch CUDA
    try:
        import torch
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                raw_name = torch.cuda.get_device_name(i)
                clean_name = raw_name.replace('\x00', '').replace('\u0000', '').strip()
                gpu_list.append({
                    "name": clean_name,
                    "backend": "CUDA (PyTorch)",
                    "identifier": f"cuda:{i}",
                    "status": "Available"
                })
    except Exception:
        pass

    # 2. PyTorch DirectML
    try:
        import torch_directml
        for i in range(torch_directml.device_count()):
            raw_name = torch_directml.device_name(i)
            clean_name = raw_name.replace('\x00', '').replace('\u0000', '').strip()
            gpu_list.append({
                "name": clean_name,
                "backend": "DirectML (PyTorch)",
                "identifier": f"privateuseone:{i}",
                "status": "Available"
            })
    except Exception:
        pass
        
    # 3. Query Windows controllers to find actual AMD/NVIDIA/Intel hardware name
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        out = subprocess.check_output(
            ["wmic", "path", "win32_VideoController", "get", "name"], 
            text=True, 
            startupinfo=startupinfo,
            stderr=subprocess.DEVNULL
        )
        lines = [line.strip().replace('\x00', '').replace('\u0000', '').strip() for line in out.split("\n") if line.strip() and "Name" not in line]
        
        for name in lines:
            if not name:
                continue
            # Deduplicate with already loaded ML backends
            if any(name.lower() in g["name"].lower() or g["name"].lower() in name.lower() for g in gpu_list):
                continue
                
            backend_compat = "Vulkan / DirectML"
            if "nvidia" in name.lower():
                backend_compat = "CUDA / Vulkan / DirectML"
            elif "amd" in name.lower() or "radeon" in name.lower():
                backend_compat = "Vulkan (LM Studio) / DirectML"
            elif "intel" in name.lower():
                backend_compat = "Vulkan / DirectML"
                
            gpu_list.append({
                "name": name,
                "backend": backend_compat,
                "identifier": "Physical Card",
                "status": "Detected"
            })
    except Exception:
        pass
        
    if not gpu_list:
        gpu_list.append({
            "name": "Standard Display Adapter",
            "backend": "CPU Fallback",
            "identifier": "Default",
            "status": "Active"
        })
        
    return gpu_list


class SystemTelemetryCollector:
    def __init__(self):
        self.is_windows = (sys.platform == "win32")
        self.hQuery = None
        self.counters = []
        self.last_rebuild = 0.0
        self.rebuild_interval = 30.0  # seconds
        self.gpu_name = "N/A"
        self.pdh = None
        
        if self.is_windows:
            try:
                self.pdh = ctypes.windll.pdh
                self._setup_pdh_functions()
                self._rebuild_pdh_query()
            except Exception as e:
                print(f"⚠️ Telemetry initialization warning (pdh.dll): {e}")
                self.pdh = None
                
        self._detect_gpu_name()
        try:
            psutil.cpu_percent(interval=None)
        except:
            pass

    def _setup_pdh_functions(self):
        self.pdh.PdhOpenQueryW.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.POINTER(PDH_HQUERY)]
        self.pdh.PdhOpenQueryW.restype = DWORD
        
        self.pdh.PdhAddCounterW.argtypes = [PDH_HQUERY, ctypes.c_wchar_p, ctypes.c_void_p, ctypes.POINTER(PDH_HCOUNTER)]
        self.pdh.PdhAddCounterW.restype = DWORD
        
        self.pdh.PdhCollectQueryData.argtypes = [PDH_HQUERY]
        self.pdh.PdhCollectQueryData.restype = DWORD
        
        self.pdh.PdhGetFormattedCounterValue.argtypes = [
            PDH_HCOUNTER,
            DWORD,
            ctypes.POINTER(DWORD),
            ctypes.POINTER(PDH_FMT_COUNTERVALUE_DOUBLE)
        ]
        self.pdh.PdhGetFormattedCounterValue.restype = DWORD
        
        self.pdh.PdhCloseQuery.argtypes = [PDH_HQUERY]
        self.pdh.PdhCloseQuery.restype = DWORD
        
        self.pdh.PdhExpandWildCardPathW.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
            ctypes.POINTER(DWORD),
            DWORD
        ]
        self.pdh.PdhExpandWildCardPathW.restype = DWORD

    def _rebuild_pdh_query(self):
        if not self.pdh:
            return
            
        if self.hQuery:
            try:
                self.pdh.PdhCloseQuery(self.hQuery)
            except Exception:
                pass
            self.hQuery = None
        self.counters = []
        
        try:
            self.hQuery = PDH_HQUERY()
            status = self.pdh.PdhOpenQueryW(None, 0, byref(self.hQuery))
            if status != 0:
                self.hQuery = None
                return
                
            wildcard_path = "\\GPU Engine(*)\\Utilization Percentage"
            buf_size = DWORD(0)
            # Fetch size needed for buffer
            status = self.pdh.PdhExpandWildCardPathW(None, wildcard_path, None, byref(buf_size), 0)
            if status != 0 and status != 0x800007D2:
                return
                
            if buf_size.value > 0:
                buf = ctypes.create_unicode_buffer(buf_size.value)
                status = self.pdh.PdhExpandWildCardPathW(None, wildcard_path, buf, byref(buf_size), 0)
                if status == 0:
                    offset = 0
                    while offset < buf_size.value:
                        s = []
                        while offset < buf_size.value and buf[offset] != '\x00':
                            s.append(buf[offset])
                            offset += 1
                        if not s:
                            break
                        path = "".join(s)
                        # We sum utilization across active 3D engines
                        if "engtype_3D" in path:
                            hCounter = PDH_HCOUNTER()
                            if self.pdh.PdhAddCounterW(self.hQuery, path, 0, byref(hCounter)) == 0:
                                self.counters.append(hCounter)
                        offset += 1
                        
            if self.counters:
                self.pdh.PdhCollectQueryData(self.hQuery)
            self.last_rebuild = time.time()
        except Exception as e:
            print(f"⚠️ Telemetry rebuild failed: {e}")
            self.hQuery = None
            self.counters = []

    def _detect_gpu_name(self):
        try:
            gpus = get_gpu_info_data_sync()
            if gpus:
                physical_gpu = next((g for g in gpus if g["identifier"] != "Default" and "CPU" not in g["backend"]), gpus[0])
                self.gpu_name = physical_gpu["name"]
        except Exception:
            self.gpu_name = "N/A"

    def _get_gpu_utilization_pdh(self) -> float:
        if not self.pdh or not self.hQuery or not self.counters:
            return 0.0
            
        # Rebuild query periodically to handle process creation/termination
        if time.time() - self.last_rebuild > self.rebuild_interval:
            self._rebuild_pdh_query()
            if not self.hQuery or not self.counters:
                return 0.0
                
        status = self.pdh.PdhCollectQueryData(self.hQuery)
        if status != 0:
            self._rebuild_pdh_query()
            if self.hQuery:
                status = self.pdh.PdhCollectQueryData(self.hQuery)
                if status != 0:
                    return 0.0
            else:
                return 0.0
                
        total_sum = 0.0
        success_count = 0
        for hC in self.counters:
            val = PDH_FMT_COUNTERVALUE_DOUBLE()
            if self.pdh.PdhGetFormattedCounterValue(hC, PDH_FMT_DOUBLE, None, byref(val)) == 0:
                if val.value.doubleValue > 0:
                    total_sum += val.value.doubleValue
                success_count += 1
                
        if len(self.counters) > 0 and success_count == 0:
            self.last_rebuild = 0.0 # Force rebuild next interval
            
        return min(total_sum, 100.0)

    def _get_gpu_utilization_nvismi(self) -> float:
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                text=True,
                startupinfo=startupinfo,
                stderr=subprocess.DEVNULL,
                timeout=1.0
            )
            return float(out.strip())
        except Exception:
            return 0.0

    def get_gpu_metrics(self) -> dict:
        gpu_util = 0.0
        if self.is_windows and self.pdh and self.counters:
            gpu_util = self._get_gpu_utilization_pdh()
        else:
            gpu_util = self._get_gpu_utilization_nvismi()
            
        return {
            "percentage": round(gpu_util, 1),
            "name": self.gpu_name
        }

    def get_system_status(self) -> dict:
        """Returns unified system metrics"""
        # 1. CPU
        try:
            cpu_percent = psutil.cpu_percent(interval=None)
        except Exception as e:
            print(f"⚠️ TELEMETRY ERROR CPU: {e}")
            cpu_percent = 0.0
            
        # 2. RAM
        try:
            mem = psutil.virtual_memory()
            memory_data = {
                "used": round(mem.used / (1024**3), 2),
                "total": round(mem.total / (1024**3), 2),
                "percentage": mem.percent
            }
        except Exception as e:
            print(f"⚠️ TELEMETRY ERROR RAM: {e}")
            memory_data = {"used": 0.0, "total": 0.0, "percentage": 0.0}
            
        # 3. Disk
        try:
            disk = psutil.disk_usage('/')
            disk_data = {
                "used": round(disk.used / (1024**3), 2),
                "total": round(disk.total / (1024**3), 2),
                "percentage": disk.percent
            }
        except Exception as e:
            print(f"⚠️ TELEMETRY ERROR DISK: {e}")
            disk_data = {"used": 0.0, "total": 0.0, "percentage": 0.0}
            
        # 4. GPU
        try:
            gpu_data = self.get_gpu_metrics()
        except Exception as e:
            print(f"⚠️ TELEMETRY ERROR GPU: {e}")
            gpu_data = {"percentage": 0.0, "name": "Error"}
        
        return {
            "cpu": {"percentage": cpu_percent},
            "memory": memory_data,
            "disk": disk_data,
            "gpu": gpu_data
        }

    def close(self):
        if self.pdh and self.hQuery:
            try:
                self.pdh.PdhCloseQuery(self.hQuery)
            except Exception:
                pass
            self.hQuery = None
            self.counters = []


# Singleton / module-level collector instance
_collector = SystemTelemetryCollector()

def get_system_status() -> dict:
    """Convenience helper to retrieve telemetry status dict"""
    return _collector.get_system_status()
