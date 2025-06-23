#!/usr/bin/env python3
# clitest.py - A generic, language-agnostic command-line test runner.

import sys
import os
import argparse
import subprocess
import re
import xml.etree.ElementTree as ET

# --- Constants for Exit Codes ---
EXIT_CODE_SUCCESS = 0
EXIT_CODE_TESTS_FAILED = 1
EXIT_CODE_RUNTIME_ERROR = 2

class TestResult:
    """A simple class to hold the result of a single test case."""
    def __init__(self, passed, message, diagnostics=None):
        self.passed = passed
        self.message = message
        self.diagnostics = diagnostics if diagnostics is not None else {}

def normalize_output(text, normalize_rules):
    """Applies a list of normalization rules to a string."""
    if not text:
        return ""
    
    rules = normalize_rules.split() if normalize_rules else []
    
    if "ansi" in rules:
        ansi_escape_pattern = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        text = ansi_escape_pattern.sub('', text)

    if "whitespace" in rules:
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
    return text

def compare_streams(actual_output, expect_element):
    """Compares actual output with an <expect> element, handling match and normalize attributes."""
    if expect_element is None:
        expected_text = ""
        match_type = "exact"
        normalize_rules = ""
    else:
        expected_text = expect_element.text or ""
        match_type = expect_element.get("match", "exact")
        normalize_rules = expect_element.get("normalize", "")

    normalized_actual = normalize_output(actual_output, normalize_rules)

    if "whitespace" in (normalize_rules.split() if normalize_rules else []):
        normalized_expected = normalize_output(expected_text, "whitespace")
    else:
        normalized_expected = expected_text

    passed = False
    failure_reason = ""

    if match_type == "exact":
        if normalized_actual == normalized_expected:
            passed = True
        else:
            failure_reason = "exact match failed"
    elif match_type == "contains":
        if normalized_expected in normalized_actual:
            passed = True
        else:
            failure_reason = "'contains' match failed"
    elif match_type == "regex":
        if re.search(normalized_expected, normalized_actual):
            passed = True
        else:
            failure_reason = "'regex' match failed"
    else:
        return False, f"Invalid match type '{match_type}'", normalized_actual, normalized_expected

    return passed, failure_reason, normalized_actual, normalized_expected


def run_command_in_env(command_text, env_vars, working_dir):
    """Executes a single setup or teardown command."""
    try:
        subprocess.run(
            command_text,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            env=env_vars,
            cwd=working_dir
        )
        return True, ""
    except subprocess.CalledProcessError as e:
        error_message = f"Command failed with exit code {e.returncode}.\n"
        error_message += f"  - Command: {e.cmd}\n"
        error_message += f"  - Stderr: {e.stderr.strip()}"
        return False, error_message
    except FileNotFoundError:
        return False, f"Command not found: '{command_text.split()[0]}'"


def run_test_case(case_element, suite_env):
    """Runs a single <test-case> and returns a TestResult object."""
    current_env = os.environ.copy()
    current_env.update(suite_env.get("variables", {}))
    
    working_dir = suite_env.get("working_dir", None)

    case_env_element = case_element.find("environment")
    if case_env_element is not None:
        case_work_dir_el = case_env_element.find("working-directory")
        if case_work_dir_el is not None and case_work_dir_el.text:
            working_dir = case_work_dir_el.text.strip()
            
        for var_el in case_env_element.findall("variable"):
            current_env[var_el.get("name")] = var_el.text or ""

        setup_el = case_env_element.find("setup")
        if setup_el is not None:
            for cmd_el in setup_el.findall("command"):
                success, msg = run_command_in_env(cmd_el.text.strip(), current_env, working_dir)
                if not success:
                    return TestResult(False, "Test case setup command failed", {"error": msg})

    command_el = case_element.find("command")
    if command_el is None or not command_el.text:
        return TestResult(False, "Missing or empty <command> tag", {})

    command_path = command_el.text.strip()
    args = [command_path]
    args_el = case_element.find("args")
    if args_el is not None:
        for arg_el in args_el.findall("arg"):
            args.append(arg_el.text or "")

    stdin_el = case_element.find("stdin")
    stdin_data = stdin_el.text if stdin_el is not None else None

    try:
        process = subprocess.run(
            args,
            capture_output=True,
            text=True,
            input=stdin_data,
            env=current_env,
            cwd=working_dir
        )
        actual_stdout = process.stdout
        actual_stderr = process.stderr
        actual_exit_code = process.returncode

    except FileNotFoundError:
        diags = {
            "error_type": "FileNotFoundError",
            "error_details": f"The command '{command_path}' could not be found.",
            "suggestion": "Ensure the <command> tag contains only the executable path and arguments are in <arg> tags."
        }
        return TestResult(False, "Command execution failed", diags)
    except Exception as e:
        return TestResult(False, f"An unexpected error occurred during command execution: {e}", {})

    if case_env_element is not None:
        teardown_el = case_env_element.find("teardown")
        if teardown_el is not None:
            for cmd_el in teardown_el.findall("command"):
                success, msg = run_command_in_env(cmd_el.text.strip(), current_env, working_dir)
                if not success:
                    return TestResult(False, "Test case teardown command failed", {"error": msg})

    expect_el = case_element.find("expect")
    if expect_el is None:
        return TestResult(False, "Missing <expect> block in test case", {})

    stdout_passed, stdout_reason, norm_actual_out, norm_expected_out = compare_streams(actual_stdout, expect_el.find("stdout"))
    if not stdout_passed:
        diags = {"reason": f"stdout {stdout_reason}", "expected": norm_expected_out, "got": norm_actual_out}
        return TestResult(False, "stdout mismatch", diags)

    stderr_passed, stderr_reason, norm_actual_err, norm_expected_err = compare_streams(actual_stderr, expect_el.find("stderr"))
    if not stderr_passed:
        diags = {"reason": f"stderr {stderr_reason}", "expected": norm_expected_err, "got": norm_actual_err}
        return TestResult(False, "stderr mismatch", diags)

    exit_code_el = expect_el.find("exit_code")
    expected_exit_code = 0 
    if exit_code_el is not None:
        if exit_code_el.text is not None:
            try:
                expected_exit_code = int(exit_code_el.text.strip())
            except (ValueError, TypeError):
                return TestResult(False, f"Invalid <exit_code> value: '{exit_code_el.text}'", {})

    if actual_exit_code != expected_exit_code:
        diags = {"expected": str(expected_exit_code), "got": str(actual_exit_code)}
        return TestResult(False, "Exit code mismatch", diags)
            
    return TestResult(True, "Test passed", {})

def run_suite(suite_path, args, is_subtest=False, pre_parsed_tree=None):
    """Parses and runs a test suite XML file."""
    # Use the pre-parsed tree if provided, otherwise parse the file.
    root = pre_parsed_tree.getroot() if pre_parsed_tree else ET.parse(suite_path).getroot()

    suite_description = root.get("description", suite_path)
    if args.verbose and not is_subtest:
        print(f"#\n# Running suite: {suite_description}\n#", file=sys.stderr)

    suite_env = {"variables": {}, "working_dir": None}
    suite_env_el = root.find("environment")
    if suite_env_el is not None:
        work_dir_el = suite_env_el.find("working-directory")
        if work_dir_el is not None and work_dir_el.text:
            suite_env["working_dir"] = work_dir_el.text.strip()
        
        setup_env = os.environ.copy()
        for var_el in suite_env_el.findall("variable"):
            var_name = var_el.get("name")
            var_value = var_el.text or ""
            suite_env["variables"][var_name] = var_value
            setup_env[var_name] = var_value
        
        setup_el = suite_env_el.find("setup")
        if setup_el is not None:
            for cmd_el in setup_el.findall("command"):
                success, msg = run_command_in_env(cmd_el.text.strip(), setup_env, suite_env["working_dir"])
                if not success:
                    print(f"Error: Suite setup command failed for '{suite_path}'.\n{msg}", file=sys.stderr)
                    return EXIT_CODE_RUNTIME_ERROR, 0

    test_cases = root.findall("./test-cases/test-case")
    if not test_cases:
        test_cases = root.findall("test-case")

    total_tests_in_suite = len(test_cases)
    
    if is_subtest:
        print(f"    1..{total_tests_in_suite}")

    suite_passed = True
    for i, case_el in enumerate(test_cases):
        test_num = i + 1
        description = case_el.get("description", "")
        
        if args.verbose and not args.quiet:
            prefix = "    " if is_subtest else ""
            print(f"{prefix}# Executing case: {description or 'Unnamed Test Case'}", file=sys.stderr)

        result = run_test_case(case_el, suite_env)
        
        indent = "    " if is_subtest else ""
        if result.passed:
            print(f"{indent}ok {test_num} - {description}")
        else:
            suite_passed = False
            print(f"{indent}not ok {test_num} - {description}")
            if not args.quiet:
                print(f"{indent}  ---")
                print(f"{indent}  message: \"{result.message}\"")
                print(f"{indent}  severity: fail")
                if result.diagnostics:
                    print(f"{indent}  data:")
                    for key, value in result.diagnostics.items():
                        value_str = str(value).replace('\n', '\\n')
                        print(f"{indent}    {key}: \"{value_str}\"")
                print(f"{indent}  ...")

    if suite_env_el is not None:
        teardown_el = suite_env_el.find("teardown")
        if teardown_el is not None:
            teardown_env = os.environ.copy()
            teardown_env.update(suite_env["variables"])
            for cmd_el in teardown_el.findall("command"):
                run_command_in_env(cmd_el.text.strip(), teardown_env, suite_env["working_dir"])

    return (EXIT_CODE_SUCCESS if suite_passed else EXIT_CODE_TESTS_FAILED), total_tests_in_suite


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="A generic, language-agnostic command-line test runner.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('suites', metavar='SUITE', nargs='+', help='One or more paths to test suite XML files.')
    
    # FIX: Use a mutually exclusive group for verbose and quiet flags.
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        '-v', '--verbose', 
        action='store_true', 
        help='Enable verbose output, printing descriptions and diagnostics.'
    )
    verbosity_group.add_argument(
        '-q', '--quiet', 
        action='store_true', 
        help='Enable quiet output, suppressing diagnostic messages on failure.'
    )
    
    args = parser.parse_args()

    # Pre-flight check for file existence and XML validity before any output.
    parsed_trees = {}
    for suite_path in args.suites:
        if not os.path.exists(suite_path):
            print(f"Error: File not found: '{suite_path}'", file=sys.stderr)
            return EXIT_CODE_RUNTIME_ERROR
        try:
            tree = ET.parse(suite_path)
            parsed_trees[suite_path] = tree
        except ET.ParseError as e:
            print(f"Error: Invalid XML in suite file '{suite_path}'.\n{e}", file=sys.stderr)
            return EXIT_CODE_RUNTIME_ERROR

    # --- Main Execution Logic ---
    print("TAP version 14")

    is_multi_suite = len(args.suites) > 1
    
    if is_multi_suite:
        print(f"1..{len(args.suites)}")

    overall_exit_code = EXIT_CODE_SUCCESS
    
    for i, suite_path in enumerate(args.suites):
        suite_tree = parsed_trees[suite_path]
        if is_multi_suite:
            suite_description = suite_tree.getroot().get("description", suite_path)
            
            suite_result_code, num_tests = run_suite(suite_path, args, is_subtest=True, pre_parsed_tree=suite_tree)
            
            if suite_result_code == EXIT_CODE_RUNTIME_ERROR:
                overall_exit_code = EXIT_CODE_RUNTIME_ERROR
                print(f"not ok {i+1} - {suite_description}")
                if not args.quiet:
                    print(f"  ---")
                    print(f"  message: \"Suite failed to execute due to a runtime or setup error.\"")
                    print(f"  ...")
                break
            elif suite_result_code == EXIT_CODE_TESTS_FAILED:
                if overall_exit_code == EXIT_CODE_SUCCESS:
                    overall_exit_code = EXIT_CODE_TESTS_FAILED
                print(f"not ok {i+1} - {suite_description}")
            else:
                print(f"ok {i+1} - {suite_description}")
        else:
            exit_code, num_tests = run_suite(suite_path, args, is_subtest=False, pre_parsed_tree=suite_tree)
            overall_exit_code = exit_code
            if exit_code != EXIT_CODE_RUNTIME_ERROR:
                print(f"1..{num_tests}")

    return overall_exit_code

if __name__ == "__main__":
    sys.exit(main())

