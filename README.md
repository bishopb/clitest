# clitest.py - A Generic Command-Line Testing Tool

`clitest.py` is a self-contained, language-agnostic test runner for command-line interface (CLI) tools. It is written in Python 3 and requires no third-party libraries, making it highly portable.

Tests are defined in a simple, expressive XML format allowing for detailed and well-documented test suites. The tool can run multiple test suites and report their results in one of several formats, including JUnit and TAP, making it easy to integrate with CI/CD systems like Jenkins, GitLab CI, and GitHub Actions.

## Features

* **Dependency-Free:** Runs anywhere with a standard Python 3 installation.
* **XML-Based Test Suites:** Create clear, commented, and structured test plans.
* **Multiple Output Formats:** Integrates seamlessly with a wide range of developer tools.
* **Full Environment Control:** Define environment variables, working directories, and setup/teardown commands to create stable and isolated tests.
* **Powerful Output Matching:** Go beyond exact string comparison with support for substring matching (`contains`), regular expressions (`regex`), and automatic normalization of whitespace and ANSI color codes.
* **Secure:** Executes commands directly without invoking a shell, preventing shell injection vulnerabilities.

## Example

The `clitest.py` code is itself tested by its own test specification:

```sh
$ python3 clitest.py clitest-*-tests.xml

  Tests for the --reporter junit feature
    ✓ Should produce valid JUnit XML for a passing suite
    ✓ Should produce valid JUnit XML for a failing suite
    ✓ Should aggregate results correctly in JUnit XML for multiple suites
    ✓ Should include verbose output in system-out for JUnit reporter

  Tests for the --reporter spec feature
    ✓ Should produce valid spec output for a passing suite
    ✓ Should produce valid spec output for a failing suite
    ✓ Should produce valid spec output for multiple suites
    ✓ Should produce verbose output with spec reporter

  Test the core features of clitest.py
    ✓ Should exit 0 and report a pass for a valid, passing suite
    ✓ Should exit 1 and report a failure for a valid, failing suite
    ✓ Should correctly process the 'normalize' attribute
    ✓ Should correctly process the 'match=regex' attribute
    ✓ Should correctly apply environment variables to subprocesses
    ✓ Should fail gracefully if the suite file is not found
    ✓ Should fail gracefully if the suite file is invalid XML
    ✓ Should show a usage error when no arguments are given
    ✓ Should produce valid TAP subtest output for multiple suites
    ✓ Should produce verbose output with --verbose flag
    ✓ Should show usage error for mutually exclusive flags --verbose and --quiet
    ✓ Should list tests with --list-tests flag and not run them

  20 tests run, 20 passing, 0 failing
```

Refer to the [clitest-tap-tests.xml](./clitest-tap-tests.xml) file for an example of how to write the test cases for a command line program. Refer to all the `clitest-*-tests.xml` files for an example of how to write different test suites for different features.

## Installation

The `clitest.py` file is a standalone test runner. No dependencies need to be installed.

Just download the `clitest.py` code from the command line and begin using it right away:

```sh
$ curl -LJO https://raw.githubusercontent.com/bishopb/clitest/refs/heads/main/clitest.py
$ python3 clitest.py -h
```

## Usage

```
usage: clitest.py [-h] [-v | -q | --list-tests] [--reporter {tap,junit,spec}] SUITE [SUITE ...]

A generic, language-agnostic command-line test runner.

positional arguments:
  SUITE                 One or more paths to test suite XML files.

options:
  -h, --help            show this help message and exit
  -v, --verbose         Enable verbose output.
  -q, --quiet           Enable quiet output.
  --list-tests          List all tests that would be run without executing them.
  --reporter {tap,junit,spec}
                        The output format for test results (default: spec).
```

* `clitest.py` is invoked from the command line, specifying one or more test suite files.
* By default, `clitest.py` will run the tests given in the test suite files.
* To simply list the cases that would be run (rather than run them), pass the * `--list-tests` option.
* By default, `spec` output is shown. Use the `--reporter` option to choose `tap` or `junit` alternatives.

## Test Suite XML Specification

A test suite file is an XML document that defines the tests to be run. Refer to the [clitest-schema.xsd](./clitest-schema.xsd) file for the formal specification.

In short:
* The clitest XML format is structured around a root `<test-suite>` element, which can contain an optional `<environment>` block for global setup, teardown, and environment variables.
* Inside the suite, a `<test-cases>` element holds one or more individual `<test-case>` blocks.
* Each test case defines a `<command>` to be run, its `<args>`, optional `<stdin>`, and a mandatory `<expect>` block that specifies the expected stdout, stderr, and exit code.
* Both stdout and stderr expectations can be modified with match (exact, contains, regex) and normalize (ansi, whitespace) attributes for flexible and robust comparisons.

### Verifying a Test Suite

The `xmllint` tool can validate a test suite XML file you create against the clitest test suite XML schema definition, like so:

```sh
$ xmllint --noout --schema clitest-schema.xsd clitest-tap-tests.xml
clitest-tap-tests.xml validates
```

### Full Example (`test-suite.xml`)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!-- 
  Reference test suite for a hypothetical 'sys-monitor' command-line tool.
-->
<test-suite description="Comprehensive tests for the 'sys-monitor' tool">

  <!-- 
    A global environment to ensure a clean state for the test run.
    This creates a directory for logs and removes it upon completion.
  -->
  <environment>
    <working-directory>/tmp/sys-monitor-tests</working-directory>
    <setup>
      <command>mkdir -p /tmp/sys-monitor-tests/logs</command>
    </setup>
    <teardown>
      <command>rm -rf /tmp/sys-monitor-tests</command>
    </teardown>
  </environment>

  <test-cases>

    <!-- Test Case 1: Simple success case with default "exact" matching. -->
    <test-case description="Should respond to ping">
      <command>./sys-monitor</command>
      <args>
        <arg>--ping</arg>
      </args>
      <expect>
        <stdout>pong</stdout>
        <exit_code>0</exit_code>
      </expect>
    </test-case>

    <!-- Test Case 2: Demonstrates output normalization and substring matching. -->
    <test-case description="Should report critical failure message, ignoring formatting">
      <command>./sys-monitor</command>
      <args>
        <arg>--check-critical</arg>
        <arg>service:auth</arg>
      </args>
      <expect>
        <stderr normalize="ansi whitespace" match="contains">CRITICAL: Service 'auth' is non-responsive.</stderr>
        <exit_code>5</exit_code>
      </expect>
    </test-case>
    
    <!-- Test Case 3: Demonstrates pattern matching for variable output. -->
    <test-case description="Should confirm log file creation with correct format">
      <command>./sys-monitor</command>
      <args>
        <arg>--log-event</arg>
        <arg>"User login"</arg>
      </args>
      <expect>
        <stdout match="regex">^Log written to /tmp/sys-monitor-tests/logs/\d{4}-\d{2}-\d{2}-\d{6}\.log$</stdout>
        <exit_code>0</exit_code>
      </expect>
    </test-case>

  </test-cases>
</test-suite>
```
