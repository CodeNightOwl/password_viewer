/* load_hook32.c - 32-bit loader for hook_reader32.dll */
#include <windows.h>
#include <stdio.h>

typedef BOOL (__stdcall *ReadPasswordFunc)(HWND, WCHAR*, int);

int wmain(int argc, wchar_t* argv[]) {
    if (argc < 2) {
        printf("Usage: load_hook32.exe <hwnd_hex>\n");
        return 1;
    }
    
    HWND hwnd = (HWND)(UINT_PTR)wcstoul(argv[1], NULL, 16);
    
    /* Get DLL path - use current directory */
    WCHAR dllPath[MAX_PATH];
    DWORD len = GetCurrentDirectoryW(MAX_PATH, dllPath);
    if (len > 0 && dllPath[len-1] != L'\\') {
        dllPath[len] = L'\\';
        dllPath[len+1] = L'\0';
    }
    wcscat(dllPath, L"hook_reader32.dll");
    
    printf("DLL: %ls\n", dllPath);
    printf("Target: 0x%p PID=%u TID=%u\n", hwnd, 
           GetProcessIdOfThread((HANDLE)(UINT_PTR)GetWindowThreadProcessId(hwnd, NULL)),
           GetWindowThreadProcessId(hwnd, NULL));
    
    WCHAR cls[256] = {0};
    GetClassNameW(hwnd, cls, 256);
    printf("Class: %ls\n", cls);
    
    /* Load DLL */
    HMODULE hDll = LoadLibraryW(dllPath);
    if (!hDll) {
        printf("LoadLibrary FAILED: %u\n", GetLastError());
        return 1;
    }
    
    ReadPasswordFunc ReadPassword = (ReadPasswordFunc)GetProcAddress(hDll, "_ReadPassword@12");
    if (!ReadPassword) {
        printf("GetProcAddress FAILED: %u\n", GetLastError());
        FreeLibrary(hDll);
        return 1;
    }
    
    printf("Calling ReadPassword...\n");
    WCHAR pwd[512] = {0};
    BOOL ret = ReadPassword(hwnd, pwd, 512);
    
    if (ret) {
        printf("\nSUCCESS! Password: %ls\n", pwd);
    } else {
        printf("\nFAILED or empty\n");
    }
    
    FreeLibrary(hDll);
    return 0;
}
