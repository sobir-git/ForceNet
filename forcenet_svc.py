import servicemanager
import win32profile
import win32ts 
import win32service
import win32serviceutil
import win32event
import win32con
import win32api
import win32security
import win32process
import pywintypes
import sys
import logging
import os
import traceback


FROZEN = getattr(sys, 'frozen', False)
if FROZEN:  APPLICATION_PATH = os.path.dirname(sys.executable)
else:       APPLICATION_PATH = "C:\\Program Files (x86)\\ForceNet"
# for testing purposes in unfrozen mode install Forcenet in above directory


logging.basicConfig(
    filename="C:\\forcenet_svc.log", 
    filemode='w', 
    format='%(asctime)s - [%(levelname)8s] \t%(message)s',
    level=logging.DEBUG,
    datefmt='%d-%b %H:%M:%S'
    )

logging.info("LOGGING SET UP")
logging.info('sys.executable: %s', sys.executable)
logging.info("FROZEN: %s", FROZEN)
logging.info("APPLICATION_PATH: %s", APPLICATION_PATH)


def run_as_user(cmd):
    logging.info("run_as_user(%s)", cmd)
    console_session_id = win32ts.WTSGetActiveConsoleSessionId()
    console_user_token = win32ts.WTSQueryUserToken(console_session_id)
    session_id = win32security.GetTokenInformation (console_user_token, win32security.TokenSessionId)
    logging.info("session_id = %s", session_id)
    process_token = win32security.OpenProcessToken (win32process.GetCurrentProcess(), win32con.MAXIMUM_ALLOWED)

    new_process_token = win32security.DuplicateTokenEx (
        process_token, 
        win32security.SecurityImpersonation,
        win32con.MAXIMUM_ALLOWED, 
        win32security.TokenPrimary,
        win32security.SECURITY_ATTRIBUTES()
        )

    id = win32security.LookupPrivilegeValue(None, win32security.SE_TCB_NAME)
    newPriv = [(id, win32security.SE_PRIVILEGE_ENABLED)]
    win32security.AdjustTokenPrivileges(new_process_token, 0, newPriv)
    
    win32security.SetTokenInformation(new_process_token, win32security.TokenSessionId, session_id)

    startup = win32process.STARTUPINFO()
    environment = win32profile.CreateEnvironmentBlock(console_user_token, False)
    priority = win32con.NORMAL_PRIORITY_CLASS
    # handle, thread_id, pid, tid = result
    result = win32process.CreateProcessAsUser(
        new_process_token, 
        cmd, 
        None, 
        None, 
        None, 
        True, 
        priority, 
        environment, 
        None, 
        startup)
    return result


def AdjustPriv(priv, htoken=None, enable=True):
    if not htoken:
        flags = win32security.TOKEN_ADJUST_PRIVILEGES | win32security.TOKEN_QUERY
        htoken = win32security.OpenProcessToken(
            win32api.GetCurrentProcess(), flags)
    id = win32security.LookupPrivilegeValue(None, priv)
    if enable:
        newPriv = [(id, win32security.SE_PRIVILEGE_ENABLED)]
    else:
        newPriv = [(id, 0)]
    win32security.AdjustTokenPrivileges(htoken, 0, newPriv)

 
class ForceNet(win32serviceutil.ServiceFramework):
    _svc_name_ = "ForceNet"
    _svc_display_name_ = "ForceNet"
    _svc_description_ = "Keep the network cable connected"

    def __init__(self, args):
        logging.info("ForceNet.__init__()")
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        # process handle
        self.pHandle = None

    def SvcStop(self):
        logging.info("ForceNet.SvcStop()")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        logging.info("ForceNet.SvcDoRun()")
        self.exepath = os.path.join(APPLICATION_PATH, "ForceNet.exe")

        import servicemanager
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE, servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))

        self.timeout = 1000  # 10 seconds
        while 1:
            logging.debug('LOOP')
            # Wait for service stop signal, if I timeout, loop again
            rc = win32event.WaitForSingleObject(self.hWaitStop, self.timeout)
            # Check to see if self.hWaitStop happened
            if rc == win32event.WAIT_OBJECT_0:
                break

            # check if process is running
            if self.pHandle is None:
                is_process_running = False
            else:
                timeout = 0
                rc = win32event.WaitForSingleObject(self.pHandle, timeout)
                if rc == win32event.WAIT_OBJECT_0:
                    logging.warning("Proceess somehow is not running!")
                    is_process_running = False
                else:
                    is_process_running = True

            if is_process_running:
                continue

            # run process
            try:
                result = run_as_user(self.exepath)
                handle, thread_id, pid, tid = result
                logging.info("Created a new process; pid: %s" % pid)
                self.pHandle = handle
            except BaseException as e:
                tb = traceback.format_exc()
                logging.error("Exception occured on main loop...")
                logging.error(tb)


def ctrlHandler(ctrlType):
   return True


if __name__ == '__main__':
    logging.debug("in __main__")
    try:
        if len(sys.argv) == 1:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(ForceNet)
            servicemanager.StartServiceCtrlDispatcher()
        else:
            win32api.SetConsoleCtrlHandler(ctrlHandler, True)
            win32serviceutil.HandleCommandLine(ForceNet)
    except BaseException:
        tb = traceback.format_exc()
        logging.error(tb)
