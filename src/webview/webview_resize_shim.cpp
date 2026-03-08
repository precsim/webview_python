// webview_resize_shim.cpp
//
// A minimal shim DLL that adds webview_resize() on top of the existing
// webview.dll. It does NOT wrap or proxy any other webview functions —
// those are still loaded directly from webview.dll by Python ctypes.
//
// It accesses the ICoreWebView2Controller via the WEBVIEW_NATIVE_HANDLE_KIND_UI_WINDOW
// HWND, then uses SendMessage to trigger a WM_SIZE so WebView2 reflows —
// OR uses the WebView2 loader to get the controller pointer via the
// known internal layout of the webview_t struct.
//
// Build (MSVC):
//   cl /LD /EHsc webview_resize_shim.cpp /link WebView2Loader.dll.lib
//
// Build (MinGW):
//   g++ -shared -o webview_resize_shim.dll webview_resize_shim.cpp -luser32

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

// ── Option A: Pure Win32 approach ────────────────────────────────────────────
// Works because WebView2 responds to WM_SIZE on its host HWND.
// webview_get_native_handle(w, UI_WINDOW) gives us the host HWND.
// We just move+resize that HWND and send WM_SIZE — WebView2 reflows.

extern "C" __declspec(dllexport)
void webview_resize(void* host_hwnd, int x, int y, int width, int height)
{
    HWND hwnd = reinterpret_cast<HWND>(host_hwnd);
    if (!hwnd) return;

    // Move and resize the WebView2 host window
    MoveWindow(hwnd, x, y, width, height, TRUE);

    // Force WebView2 to reflow its content to the new size
    // WebView2 listens to WM_SIZE on its host HWND
    SendMessage(hwnd, WM_SIZE, SIZE_RESTORED,
        MAKELPARAM((WORD)width, (WORD)height));
}

// ── Option B: Use ICoreWebView2Controller::put_Bounds directly ───────────────
// This requires linking against WebView2Loader.dll and including WebView2.h.
// Uncomment this block and comment out Option A if you want the controller API.
//
// #include <wrl.h>
// #include <WebView2.h>
//
// extern "C" __declspec(dllexport)
// void webview_resize_controller(void* controller_ptr,
//                                int x, int y, int width, int height)
// {
//     auto* ctrl = reinterpret_cast<ICoreWebView2Controller*>(controller_ptr);
//     if (!ctrl) return;
//     RECT bounds = { x, y, x + width, y + height };
//     ctrl->put_Bounds(bounds);
// }

BOOL WINAPI DllMain(HINSTANCE, DWORD, LPVOID) { return TRUE; }
