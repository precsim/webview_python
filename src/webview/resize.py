import sys
import ctypes
from pathlib import Path
from ._webview_ffi import WebviewNativeHandleKind

def _load_resize_shim():
    """Load the resize shim for the current platform."""
    names = {
        "win32":  "webview_resize_shim.dll",
        "linux":  "webview_resize_shim.so",
        "darwin": "webview_resize_shim.dylib",
    }
    shim_name = names.get(sys.platform)
    if not shim_name:
        raise OSError(f"Unsupported platform: {sys.platform}")
    shim_path = Path(__file__).parent / shim_name
    if not shim_path.exists():
        raise FileNotFoundError(
            f"{shim_name} not found at {shim_path}. "
            "Please build it via the GitHub Actions workflow."
        )
    lib = ctypes.cdll.LoadLibrary(str(shim_path))
    lib.webview_resize.argtypes = [ctypes.c_void_p,  # host HWND
                                   ctypes.c_int,      # x
                                   ctypes.c_int,      # y
                                   ctypes.c_int,      # width
                                   ctypes.c_int]      # height
    lib.webview_resize.restype = None
    return lib

# Lazily loaded — only initialised on first call on Windows
_shim = None

def resize_webview(wv, x: int, y: int, width: int, height: int):
    """
    Resize an embedded webview to the given bounds.

    Parameters
    ----------
    wv     : Webview instance (from webview_python)
    x, y   : top-left offset within the parent window
    width  : new width in pixels
    height : new height in pixels

    Usage in a Tkinter <Configure> handler
    ---------------------------------------
    def on_resize(event):
        if str(event.widget) == ".":
            resize_webview(wv, 0, toolbar_height,
                           event.width, event.height - toolbar_height)
    """
    global _shim

    if sys.platform == "win32":
        # Get the host HWND (UI_WINDOW, not UI_WIDGET) —
        # this is what WebView2 listens to for WM_SIZE
        host_hwnd = wv.get_native_handle(
            WebviewNativeHandleKind.UI_WINDOW
        )
        if _shim is None:
            _shim = _load_resize_shim()
        _shim.webview_resize(host_hwnd, x, y, width, height)

    elif sys.platform == "linux":
        # Get the GtkWidget* for the webview widget
        widget = wv.get_native_handle(
            WebviewNativeHandleKind.UI_WIDGET
        )
        libgtk = ctypes.cdll.LoadLibrary("libgtk-3.so.0")

        class GdkRectangle(ctypes.Structure):
            _fields_ = [("x",      ctypes.c_int),
                        ("y",      ctypes.c_int),
                        ("width",  ctypes.c_int),
                        ("height", ctypes.c_int)]

        rect = GdkRectangle(x, y, width, height)
        libgtk.gtk_widget_size_allocate(widget, ctypes.byref(rect))
        # Note: X11 only — Wayland is not supported

    elif sys.platform == "darwin":
        # Get the NSView* for the webview widget
        ptr = wv.get_native_handle(
            WebviewNativeHandleKind.UI_WIDGET
        )
        import objc
        from AppKit import NSRect, NSPoint, NSSize
        nsview = objc.objc_object(c_void_p=ptr)
        nsview.setFrame_(NSRect(NSPoint(x, y), NSSize(width, height)))
