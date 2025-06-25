# clitest.py - Test any command line program against a test suite you define.

# This program allows you to define a suite of tests in one or more XML "test
# suite" files, execute them against a command line program under test, and then
# report the results in various formats.
#
# Do not run it with an XML test suite file that you have not fully vetted. It
# is a powerful tool for a trusted development environment, but it is not
# hardened against malicious input.

import sys
import os
import argparse
import subprocess
import re
import xml.etree.ElementTree as ET
import time
import html

# --- Constants for Exit Codes ---
EXIT_CODE_SUCCESS = 0
EXIT_CODE_TESTS_FAILED = 1
EXIT_CODE_RUNTIME_ERROR = 2

# --- Constants for Normalization ---
VALID_NORMALIZERS = {'ansi', 'whitespace'}

# --- ANSI Color Helper ---
class Ansi:
    """A helper class for adding ANSI color codes to text."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

    @staticmethod
    def green(s): return f"{Ansi.GREEN}{s}{Ansi.RESET}"
    @staticmethod
    def red(s): return f"{Ansi.RED}{s}{Ansi.RESET}"
    @staticmethod
    def cyan(s): return f"{Ansi.CYAN}{s}{Ansi.RESET}"
    @staticmethod
    def yellow(s): return f"{Ansi.YELLOW}{s}{Ansi.RESET}"

# --- Data Classes for Results ---

class TestCaseResult:
    """A simple class to hold the result of a single test case."""
    def __init__(self, description, classname, passed=False, message="", diagnostics=None, duration=0, log=None):
        self.description = description
        self.classname = classname
        self.passed = passed
        self.message = message
        self.diagnostics = diagnostics if diagnostics is not None else {}
        self.duration = duration
        self.log = log if log is not None else []

class SuiteResult:
    """A simple class to hold the results of a test suite."""
    def __init__(self, description, path, test_cases=None, duration=0, error=""):
        self.description = description
        self.path = path
        self.test_cases = test_cases if test_cases is not None else []
        self.duration = duration
        self.error = error

    @property
    def num_tests(self):
        return len(self.test_cases)

    @property
    def num_failures(self):
        return len([tc for tc in self.test_cases if not tc.passed])

# --- Reporter Classes ---

class TapReporter:
    """Generates standard TAP 14 output."""
    def render(self, suite_results, args):
        is_multi_suite = len(suite_results) > 1

        print("TAP version 14")
        if is_multi_suite:
            print(f"1..{len(suite_results)}")

        for i, suite_result in enumerate(suite_results):
            if suite_result.error:
                if is_multi_suite:
                    print(f"not ok {i+1} - {suite_result.description}")
                print(f"# {suite_result.error}", file=sys.stderr)
                continue

            indent = "    " if is_multi_suite else ""
            if is_multi_suite:
                print(f"ok {i+1} - {suite_result.description}" if suite_result.num_failures == 0 else f"not ok {i+1} - {suite_result.description}")
                print(f"{indent}1..{suite_result.num_tests}")
            else:
                print(f"1..{suite_result.num_tests}")

            for j, tc in enumerate(suite_result.test_cases):
                test_num = j + 1
                for log_line in tc.log:
                    print(f"{indent}{log_line}", file=sys.stderr)
                if tc.passed:
                    print(f"{indent}ok {test_num} - {tc.description}")
                else:
                    print(f"{indent}not ok {test_num} - {tc.description}")
                    if not args.quiet:
                        print(f"{indent}  ---")
                        print(f"{indent}  message: \"{tc.message}\"")
                        print(f"{indent}  severity: fail")
                        if tc.diagnostics:
                            print(f"{indent}  data:")
                            for key, value in tc.diagnostics.items():
                                value_str = str(value).replace('\n', '\\n')
                                print(f"{indent}    {key}: \"{value_str}\"")
                        print(f"{indent}  ...")

class JUnitReporter:
    """Generates JUnit XML output for CI/CD systems."""
    def render(self, suite_results, args):
        total_tests = sum(sr.num_tests for sr in suite_results)
        total_failures = sum(sr.num_failures for sr in suite_results)
        total_duration = sum(sr.duration for sr in suite_results)

        root_attrs = { "tests": str(total_tests), "failures": str(total_failures), "time": f"{total_duration:.3f}", "name": "clitest.py suites" }
        root = ET.Element("testsuites", root_attrs)

        for suite_result in suite_results:
            suite_attrs = { "name": suite_result.description, "tests": str(suite_result.num_tests), "failures": str(suite_result.num_failures), "time": f"{suite_result.duration:.3f}", "hostname": "localhost" }
            suite_el = ET.SubElement(root, "testsuite", suite_attrs)

            for tc in suite_result.test_cases:
                case_attrs = { "classname": tc.classname, "name": tc.description, "time": f"{tc.duration:.3f}" }
                case_el = ET.SubElement(suite_el, "testcase", case_attrs)

                if tc.log:
                    so_el = ET.SubElement(case_el, "system-out")
                    so_el.text = "\n".join(tc.log)

                if not tc.passed:
                    tag = "error" if tc.diagnostics.get("error_type") in ("TimeoutExpired", "ConfigurationError") else "failure"
                    failure_attrs = {"message": tc.message, "type": tc.diagnostics.get("error_type", "AssertionError")}
                    failure_el = ET.SubElement(case_el, tag, failure_attrs)
                    diag_text = "\n".join(f"{key}: {value}" for key, value in tc.diagnostics.items())
                    failure_el.text = diag_text

        ET.indent(root)
        xml_string = ET.tostring(root, encoding="unicode", xml_declaration=True, short_empty_elements=False)
        print(xml_string)

class SpecReporter:
    """Generates a human-readable spec-style report."""
    def render(self, suite_results, args):
        failures = []
        total_tests = 0
        
        for suite_result in suite_results:
            print(f"\n  {Ansi.cyan(suite_result.description)}")
            if suite_result.error:
                print(f"    {Ansi.red('ERROR:')} {suite_result.error}")
                continue

            for tc in suite_result.test_cases:
                total_tests += 1
                for log_line in tc.log:
                    print(f"    {log_line}", file=sys.stderr)
                
                if tc.passed:
                    print(f"    {Ansi.green('✓')} {tc.description}")
                else:
                    failures.append(tc)
                    print(f"    {Ansi.red(f'{len(failures)}) {tc.description}')}")

        print(f"\n\n  {total_tests} tests run, {Ansi.green(f'{total_tests - len(failures)} passing')}, {Ansi.red(f'{len(failures)} failing')}")

        if failures and not args.quiet:
            print(f"\n  {Ansi.red('Failure Details:')}\n")
            for i, tc in enumerate(failures):
                print(f"  {i+1}) {Ansi.red(tc.description)}")
                print(f"      {Ansi.yellow('Message:')} {tc.message}")
                if tc.diagnostics:
                    for key, value in tc.diagnostics.items():
                        print(f"      {Ansi.yellow(f'{key.capitalize()}:')} {value}")
                print()


# --- Manual Validation Logic ---

def _is_non_empty_string(text):
    return text and text.strip()

def _validate_element(element, known_children, known_attrs):
    """Helper to check for unknown children and attributes."""
    errors = []
    child_tags = {child.tag for child in element}
    unknown_children = child_tags - known_children
    if unknown_children:
        errors.append(f"<{element.tag}> contains unknown child element(s): {sorted(list(unknown_children))}")
    
    unknown_attrs = set(element.attrib.keys()) - known_attrs
    if unknown_attrs:
        errors.append(f"<{element.tag}> contains unknown attribute(s): {sorted(list(unknown_attrs))}")
    return errors

def _validate_stream(element):
    errors = _validate_element(element, known_children=set(), known_attrs={'match', 'normalize'})
    if 'match' in element.attrib and element.get('match') not in {'exact', 'contains', 'regex'}:
        errors.append(f"<{element.tag}> has invalid 'match' attribute value: '{element.get('match')}'")
    
    # This is the "Phase 2" semantic validation for normalize
    if 'normalize' in element.attrib:
        rules = {rule.strip().lower() for rule in element.get('normalize', '').split(',') if rule.strip()}
        invalid_rules = rules - VALID_NORMALIZERS
        if invalid_rules:
            errors.append(f"<{element.tag}> has invalid 'normalize' keyword(s): {sorted(list(invalid_rules))}")
    return errors

def _validate_expect(element):
    errors = _validate_element(element, known_children={'stdout', 'stderr', 'exit_code'}, known_attrs=set())
    if not list(element):
        errors.append("<expect> block cannot be empty.")
    
    for child_tag in ['stdout', 'stderr', 'exit_code']:
        if len(element.findall(child_tag)) > 1:
            errors.append(f"<expect> block has multiple <{child_tag}> children; only one is allowed.")

    if (el := element.find('stdout')) is not None: errors.extend(_validate_stream(el))
    if (el := element.find('stderr')) is not None: errors.extend(_validate_stream(el))
    if (el := element.find('exit_code')) is not None:
        try:
            int(el.text.strip())
        except (ValueError, AttributeError):
            errors.append("<exit_code> must contain a valid integer.")
    return errors

def _validate_test_case(element):
    known_children = {'environment', 'command', 'args', 'stdin', 'expect'}
    errors = _validate_element(element, known_children, {'description', 'timeout'})
    
    if (timeout_str := element.get('timeout')):
        try: float(timeout_str)
        except (ValueError, TypeError): errors.append("<test-case> has an invalid 'timeout' attribute.")

    if (cmd := element.find('command')) is None:
        errors.append("<test-case> is missing required <command> child.")
    elif not _is_non_empty_string(cmd.text):
        errors.append("<command> tag cannot be empty.")

    if (args_el := element.find('args')) is not None:
        if not args_el.findall('arg'):
             errors.append("<args> must contain at least one <arg> tag.")
        for arg in args_el.findall('arg'):
            if not _is_non_empty_string(arg.text):
                errors.append("<arg> tag cannot be empty.")
    
    if (expect := element.find('expect')) is None:
        errors.append("<test-case> is missing required <expect> child.")
    else:
        errors.extend(_validate_expect(expect))
    
    return errors

def validate_suite_manually(suite_path):
    """Manually validate a suite file against the schema rules."""
    try:
        tree = ET.parse(suite_path)
        root = tree.getroot()
    except ET.ParseError as e:
        return None, [f"XML is not well-formed: {e}"]
    
    errors = []
    if root.tag != 'test-suite':
        return None, [f"Invalid root element. Expected <test-suite>, but found <{root.tag}>."]

    errors.extend(_validate_element(root, {'environment', 'test-cases'}, {'description', 'timeout'}))
    if (timeout_str := root.get('timeout')):
        try: float(timeout_str)
        except (ValueError, TypeError): errors.append("<test-suite> has an invalid 'timeout' attribute.")

    if (tc_wrapper := root.find('test-cases')) is None:
        errors.append("<test-suite> is missing required <test-cases> child.")
    else:
        errors.extend(_validate_element(tc_wrapper, {'test-case'}, set()))
        for i, case_el in enumerate(tc_wrapper.findall('test-case')):
            case_errors = _validate_test_case(case_el)
            if case_errors:
                desc = case_el.get('description', f'at index {i}')
                errors.append(f"Invalid test case '{desc}':")
                errors.extend([f"  - {e}" for e in case_errors])

    return tree, errors

# --- Test Execution Logic (Refactored) ---

def normalize_output(text, normalize_rules_set):
    if not text: return ""
    if "ansi" in normalize_rules_set: text = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)
    if "whitespace" in normalize_rules_set: text = re.sub(r'\s+', ' ', text).strip()
    return text

def compare_streams(actual_output, expect_element):
    # This function is now only called if the expect_element is guaranteed to exist and be valid.
    expected_text = expect_element.text or ""
    match_type = expect_element.get("match", "exact")
    normalize_rules_str = expect_element.get("normalize", "")
    
    normalize_rules = {rule.strip().lower() for rule in normalize_rules_str.split(',') if rule.strip()}
    
    normalized_actual = normalize_output(actual_output, normalize_rules)
    normalized_expected = normalize_output(expected_text, normalize_rules) if "whitespace" in normalize_rules else expected_text

    passed = False
    if match_type == "exact" and normalized_actual == normalized_expected: passed = True
    elif match_type == "contains" and normalized_expected in normalized_actual: passed = True
    elif match_type == "regex" and re.search(normalized_expected, normalized_actual): passed = True
    
    reason = f"'{match_type}' match failed" if not passed else ""
    return passed, reason, normalized_actual, normalized_expected, {}

def run_command_in_env(command_text, env_vars, working_dir):
    try:
        subprocess.run(command_text, shell=True, check=True, capture_output=True, text=True, env=env_vars, cwd=working_dir)
        return True, ""
    except subprocess.CalledProcessError as e:
        return False, f"Command '{e.cmd}' failed with exit code {e.returncode}:\n{e.stderr.strip()}"
    except FileNotFoundError:
        return False, f"Command not found: '{command_text.split()[0]}'"

def run_test_case(case_element, suite_env, log_messages=None) -> TestCaseResult:
    start_time = time.time()
    description = case_element.get("description", "Unnamed Test Case")
    classname = suite_env.get("description", "DefaultSuite")
    log = log_messages if log_messages is not None else []

    def fail_early(message, diags=None):
        duration = time.time() - start_time
        return TestCaseResult(description, classname, passed=False, message=message, diagnostics=diags, duration=duration, log=log)

    current_env, working_dir = os.environ.copy(), suite_env.get("working_dir")
    current_env.update(suite_env.get("variables", {}))
    
    timeout_val = suite_env.get("timeout", None)
    if (case_timeout_str := case_element.get("timeout")):
        timeout_val = float(case_timeout_str) # Validation ensures this is a valid decimal/float

    if (case_env_element := case_element.find("environment")) is not None:
        if (case_work_dir_el := case_env_element.find("working-directory")) is not None and case_work_dir_el.text:
            working_dir = case_work_dir_el.text.strip()
        if (variables_el := case_env_element.find("variables")) is not None:
            for var_el in variables_el.findall("variable"):
                current_env[var_el.get("name")] = var_el.text or ""
        if (setup_el := case_env_element.find("setup")) is not None:
            for cmd_el in setup_el.findall("command"):
                success, msg = run_command_in_env(cmd_el.text, current_env, working_dir)
                if not success: return fail_early("Test case setup command failed", {"error_type": "ConfigurationError", "error": msg})
    
    command_el = case_element.find("command") # Guaranteed to exist by validation
    
    args = [command_el.text.strip()]
    
    if (args_el := case_element.find("args")) is not None:
        for arg_el in args_el.findall("arg"):
            args.append(arg_el.text) # Guaranteed non-empty by validation
    
    stdin_data = (stdin_el.text if (stdin_el := case_element.find("stdin")) is not None else None)

    try:
        process = subprocess.run(args, capture_output=True, text=True, input=stdin_data, env=current_env, cwd=working_dir, timeout=timeout_val)
    except subprocess.TimeoutExpired:
        diags = {"error_type": "TimeoutExpired", "details": f"Test case exceeded the specified timeout of {timeout_val} seconds."}
        return fail_early("Test command timed out", diags)
    except FileNotFoundError:
        return fail_early("Command execution failed", {"suggestion": f"Ensure <command> '{args[0]}' is a valid executable path."})
    except Exception as e:
        return fail_early(f"Unexpected error during execution: {e}")

    if (case_env_element := case_element.find("environment")) is not None and (teardown_el := case_env_element.find("teardown")) is not None:
        for cmd_el in teardown_el.findall("command"):
            success, msg = run_command_in_env(cmd_el.text, current_env, working_dir)
            if not success: return fail_early("Test case teardown command failed", {"error_type": "ConfigurationError", "error": msg})

    expect_el = case_element.find("expect") # Guaranteed to exist by validation
    
    if (stdout_expect_el := expect_el.find("stdout")) is not None:
        stdout_passed, stdout_reason, norm_out, norm_exp_out, _ = compare_streams(process.stdout, stdout_expect_el)
        if not stdout_passed:
            diags = {"reason": stdout_reason, "expected": norm_exp_out, "got": norm_out}
            return fail_early("stdout mismatch", diags)
    
    if (stderr_expect_el := expect_el.find("stderr")) is not None:
        stderr_passed, stderr_reason, norm_err, norm_exp_err, _ = compare_streams(process.stderr, stderr_expect_el)
        if not stderr_passed:
            diags = {"reason": stderr_reason, "expected": norm_exp_err, "got": norm_err}
            return fail_early("stderr mismatch", diags)
    
    if (exit_code_el := expect_el.find("exit_code")) is not None:
        expected_exit_code = int(exit_code_el.text.strip()) # Validation ensures this is an int
        
        if process.returncode != expected_exit_code:
            return fail_early("Exit code mismatch", {"expected": str(expected_exit_code), "got": str(process.returncode)})
            
    return TestCaseResult(description, classname, passed=True, duration=time.time() - start_time, log=log)

def run_suite(suite_path, pre_parsed_tree, args) -> SuiteResult:
    start_time = time.time()
    root = pre_parsed_tree.getroot()
    suite_description = root.get("description", suite_path)
    suite_result = SuiteResult(suite_description, suite_path)

    suite_env = {"variables": {}, "working_dir": None, "description": suite_description, "timeout": None}
    
    if (suite_timeout_str := root.get("timeout")):
        suite_env["timeout"] = float(suite_timeout_str)

    if (suite_env_el := root.find("environment")) is not None:
        if (work_dir_el := suite_env_el.find("working-directory")) is not None and work_dir_el.text:
            suite_env["working_dir"] = work_dir_el.text.strip()
        setup_env = os.environ.copy()
        if (variables_el := suite_env_el.find("variables")) is not None:
            for var_el in variables_el.findall("variable"):
                suite_env["variables"][var_el.get("name")] = var_el.text or ""
        setup_env.update(suite_env["variables"])
        if (setup_el := suite_env_el.find("setup")) is not None:
            for cmd_el in setup_el.findall("command"):
                success, msg = run_command_in_env(cmd_el.text, setup_env, suite_env["working_dir"])
                if not success:
                    suite_result.error = f"Suite setup failed: {msg}"
                    suite_result.duration = time.time() - start_time
                    return suite_result

    test_cases_wrapper = root.find('test-cases')

    for case_el in test_cases_wrapper.findall('test-case'):
        log_messages = []
        if args.verbose:
            description = case_el.get("description", "Unnamed Test Case")
            log_messages.append(f"# Executing case: {description}")
        suite_result.test_cases.append(run_test_case(case_el, suite_env, log_messages))

    if (suite_env_el := root.find("environment")) is not None and (teardown_el := suite_env_el.find("teardown")) is not None:
        teardown_env = os.environ.copy()
        teardown_env.update(suite_env["variables"])
        for cmd_el in teardown_el.findall("command"):
            run_command_in_env(cmd_el.text, teardown_env, suite_env["working_dir"])
    
    suite_result.duration = time.time() - start_time
    return suite_result

def list_cases(parsed_trees):
    print("The following tests would be run:")
    for path, tree in parsed_trees.items():
        root = tree.getroot()
        
        suite_description = root.get("description", path)
        print(f"\nSuite: {suite_description}")

        test_cases_wrapper = root.find('test-cases')
        test_cases = test_cases_wrapper.findall('test-case')
        
        if not test_cases:
            print("  (No test cases found)")
            continue
        for case_el in test_cases:
            print(f"  - {case_el.get('description', 'Unnamed Test Case')}")

def main():
    parser = argparse.ArgumentParser(description="A generic, language-agnostic command-line test runner.", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('suites', metavar='SUITE', nargs='+', help='One or more paths to test suite XML files.')
    
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output.')
    mode_group.add_argument('-q', '--quiet', action='store_true', help='Enable quiet output.')
    mode_group.add_argument('--list-cases', action='store_true', help='List all test cases that would be run without executing them.')
    
    parser.add_argument('--reporter', choices=['tap', 'junit', 'spec'], default='spec', help='The output format for test results (default: %(default)s).')
    
    args = parser.parse_args()

    parsed_trees = {}
    has_errors = False
    for suite_path in args.suites:
        if not os.path.exists(suite_path):
            print(f"Error: File not found: '{suite_path}'", file=sys.stderr)
            has_errors = True
            continue
        
        tree, errors = validate_suite_manually(suite_path)
        if errors:
            print(f"Error: Validation failed for suite '{suite_path}':", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            has_errors = True
            continue

        parsed_trees[suite_path] = tree
    
    if has_errors:
        return EXIT_CODE_RUNTIME_ERROR

    if args.list_cases:
        list_cases(parsed_trees)
        return EXIT_CODE_SUCCESS

    all_suite_results = [run_suite(path, tree, args) for path, tree in parsed_trees.items()]

    overall_exit_code = EXIT_CODE_SUCCESS
    if any(sr.error for sr in all_suite_results): overall_exit_code = EXIT_CODE_RUNTIME_ERROR
    elif any(sr.num_failures > 0 for sr in all_suite_results): overall_exit_code = EXIT_CODE_TESTS_FAILED

    reporters = {'tap': TapReporter, 'junit': JUnitReporter, 'spec': SpecReporter}
    reporters[args.reporter]().render(all_suite_results, args)

    return overall_exit_code

if __name__ == "__main__":
    sys.exit(main())
