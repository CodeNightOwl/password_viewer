/* load_hook64.c - 64-bit loader for hook_reader.dll */
#include <windows.h>
#include <stdio.h>

typedef BOOL (__stdcall *ReadPasswordFunc)(HWND hwnd, WCHAR* outBuf, int bufSize, int timeoutMs);

int wmain(int argc, wchar_t* argv[]) {
    if (argc < 2) {
        printf("Usage: load_hook64.exe <hwnd_hex>\n");
        return 1;
    }

    HWND hwnd = (HWND)(UINT_PTR)_wcstoui64(argv[1], NULL, 16);

    /* Get DLL path */
    WCHAR dllPath[MAX_PATH];
    DWORD len = GetCurrentDirectoryW(MAX_PATH, dllPath);
    if (len > 0 && dllPath[len-1] != L'\\') {
        dllPath[len] = L'\\';
        dllPath[len+1] = L'\0';
    }
    wcscat(dllPath, L"hook_reader.dll");

    /* Load DLL */
    HMODULE hDll = LoadLibraryW(dllPath);
    if (!hDll) {
        printf("LoadLibrary FAILED: %u\n", GetLastError());
        return 1;
    }

    ReadPasswordFunc ReadPasswordDirect = (ReadPasswordFunc)GetProcAddress(hDll, "ReadPasswordDirect");
    ReadPasswordFunc ReadPasswordViaHook = (ReadPasswordFunc)GetProcAddress(hDll, "ReadPasswordViaHook");

    if (!ReadPasswordDirect && !ReadPasswordViaHook) {
        printf("GetProcAddress FAILED: %u\n", GetLastError());
        FreeLibrary(hDll);
        return 1;
    }

    WCHAR pwd[512] = {0};
    BOOL ret = FALSE;

    /* Try direct read first */
    if (ReadPasswordDirect) {
        ret = ReadPasswordDirect(hwnd, pwd, 512, 3000);
    }

    /* Fallback to hook injection */
    if (!ret && ReadPasswordViaHook) {
        ZeroMemory(pwd, sizeof(pwd));
        ret = ReadPasswordViaHook(hwnd, pwd, 512, 3000);
    }

    if (ret && pwd[0] != 0) {
        printf("SUCCESS! Password: %ls\n", pwd);
    } else {
        printf("FAILED or empty\n");
    }

    FreeLibrary(hDll);
    return 0;
}
