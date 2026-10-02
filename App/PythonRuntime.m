#import "PythonRuntime.h"
#include <Python/Python.h>

static PyObject *gDispatch = NULL;
static BOOL gStarted = NO;

static NSString *DescribeStatus(PyStatus status) {
    return [NSString stringWithFormat:@"%s: %s",
            status.func ? status.func : "python", status.err_msg ? status.err_msg : "unknown error"];
}

static NSString *ConsumePythonError(void) {
    PyObject *exc = PyErr_GetRaisedException();
    if (exc == NULL) {
        return @"unknown Python error";
    }
    NSMutableString *out = [NSMutableString string];
    PyObject *type = (PyObject *)Py_TYPE(exc);
    PyObject *typeName = PyObject_GetAttrString(type, "__name__");
    if (typeName) {
        const char *c = PyUnicode_AsUTF8(typeName);
        if (c) { [out appendFormat:@"%s: ", c]; }
        Py_DECREF(typeName);
    }
    PyObject *str = PyObject_Str(exc);
    if (str) {
        const char *c = PyUnicode_AsUTF8(str);
        if (c) { [out appendString:[NSString stringWithUTF8String:c] ?: @""]; }
        Py_DECREF(str);
    }
    PyErr_Clear();

    PyObject *tbModule = PyImport_ImportModule("traceback");
    if (tbModule) {
        PyObject *lines = PyObject_CallMethod(tbModule, "format_exception", "O", exc);
        if (lines) {
            PyObject *sep = PyUnicode_FromString("");
            PyObject *joined = sep ? PyUnicode_Join(sep, lines) : NULL;
            if (joined) {
                const char *c = PyUnicode_AsUTF8(joined);
                if (c) { [out appendFormat:@"\n%@", [NSString stringWithUTF8String:c] ?: @""]; }
                Py_DECREF(joined);
            }
            Py_XDECREF(sep);
            Py_DECREF(lines);
        }
        Py_DECREF(tbModule);
    }
    PyErr_Clear();
    Py_DECREF(exc);
    return out;
}

static PyStatus AppendPath(PyConfig *config, NSString *path) {
    wchar_t *wide = Py_DecodeLocale([path UTF8String], NULL);
    if (wide == NULL) {
        return PyStatus_Error("cannot decode path");
    }
    PyStatus st = PyWideStringList_Append(&config->module_search_paths, wide);
    PyMem_RawFree(wide);
    return st;
}

@implementation PythonRuntime

+ (nullable NSString *)start {
    if (gStarted) { return nil; }

    NSBundle *bundle = [NSBundle mainBundle];
    NSString *resources = [bundle resourcePath];
    NSString *pythonHome = [resources stringByAppendingPathComponent:@"python"];
    NSString *appDir = [resources stringByAppendingPathComponent:@"app"];
    NSString *pkgDir = [resources stringByAppendingPathComponent:@"app_packages"];

    NSString *libRoot = [pythonHome stringByAppendingPathComponent:@"lib"];
    NSString *tag = nil;
    for (NSString *name in [[NSFileManager defaultManager] contentsOfDirectoryAtPath:libRoot error:nil]) {
        if ([name hasPrefix:@"python3."]) { tag = name; }
    }
    if (tag == nil) {
        return [NSString stringWithFormat:@"Python standard library not found in %@ "
                "(the 'Process Python libraries' build phase did not run?)", libRoot];
    }
    NSString *stdlib = [libRoot stringByAppendingPathComponent:tag];
    NSString *dynload = [stdlib stringByAppendingPathComponent:@"lib-dynload"];

    setenv("UABE_BUNDLE_PATH", [[bundle bundlePath] UTF8String], 1);
    setenv("PYTHONDONTWRITEBYTECODE", "1", 1);

    PyPreConfig preconfig;
    PyPreConfig_InitIsolatedConfig(&preconfig);
    preconfig.utf8_mode = 1;
    preconfig.configure_locale = 0;
    PyStatus status = Py_PreInitialize(&preconfig);
    if (PyStatus_Exception(status)) { return DescribeStatus(status); }

    PyConfig config;
    PyConfig_InitIsolatedConfig(&config);
    config.write_bytecode = 0;
    config.buffered_stdio = 0;
    config.install_signal_handlers = 0;

    status = PyConfig_SetBytesString(&config, &config.home, [pythonHome UTF8String]);
    if (PyStatus_Exception(status)) { PyConfig_Clear(&config); return DescribeStatus(status); }

    status = PyConfig_Read(&config);
    if (PyStatus_Exception(status)) { PyConfig_Clear(&config); return DescribeStatus(status); }

    config.module_search_paths_set = 1;
    for (NSString *p in @[stdlib, dynload, appDir, pkgDir]) {
        status = AppendPath(&config, p);
        if (PyStatus_Exception(status)) { PyConfig_Clear(&config); return DescribeStatus(status); }
    }

    status = Py_InitializeFromConfig(&config);
    PyConfig_Clear(&config);
    if (PyStatus_Exception(status)) { return DescribeStatus(status); }

    NSString *error = nil;
    PyObject *module = PyImport_ImportModule("uabe_backend");
    if (module == NULL) {
        error = [NSString stringWithFormat:@"import uabe_backend failed: %@", ConsumePythonError()];
    } else {
        gDispatch = PyObject_GetAttrString(module, "dispatch");
        Py_DECREF(module);
        if (gDispatch == NULL) {
            error = [NSString stringWithFormat:@"uabe_backend.dispatch missing: %@", ConsumePythonError()];
        }
    }

    PyEval_SaveThread();

    if (error == nil) { gStarted = YES; }
    return error;
}

+ (NSString *)callMethod:(NSString *)method payload:(NSString *)payload {
    if (!gStarted || gDispatch == NULL) {
        return @"{\"ok\":false,\"error\":\"Python is not running\"}";
    }
    NSString *result = nil;
    PyGILState_STATE gil = PyGILState_Ensure();
    PyObject *reply = PyObject_CallFunction(gDispatch, "ss", [method UTF8String], [payload UTF8String]);
    if (reply == NULL) {
        NSString *msg = ConsumePythonError();
        NSData *json = [NSJSONSerialization dataWithJSONObject:@{@"ok": @NO, @"error": msg}
                                                       options:0 error:nil];
        result = [[NSString alloc] initWithData:json encoding:NSUTF8StringEncoding];
    } else {
        const char *c = PyUnicode_AsUTF8(reply);
        result = c ? [NSString stringWithUTF8String:c] : nil;
        Py_DECREF(reply);
    }
    PyGILState_Release(gil);
    return result ?: @"{\"ok\":false,\"error\":\"Empty reply from Python\"}";
}

@end
