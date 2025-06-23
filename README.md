# clitest.py - A Generic Command-Line Testing Tool

`clitest.py` is a self-contained, language-agnostic test runner for command-line interface (CLI) tools. It is written in Python 3 and requires no third-party libraries, making it highly portable.

Tests are defined in a simple, expressive XML format, allowing for detailed and well-documented test suites. The tool reports its results using the standard [Test Anything Protocol (TAP)](https://testanything.org/), making it easy to integrate with CI/CD systems like Jenkins, GitLab CI, and GitHub Actions.

## Features

* **Dependency-Free:** Runs anywhere with a standard Python 3 installation.
* **XML-Based Test Suites:** Create clear, commented, and structured test plans.
* **TAP-Compliant Output:** Integrates seamlessly with a wide range of developer tools.
* **Full Environment Control:** Define environment variables, working directories, and setup/teardown commands to create stable and isolated tests.
* **Powerful Output Matching:** Go beyond exact string comparison with support for substring matching (`contains`), regular expressions (`regex`), and automatic normalization of whitespace and ANSI color codes.
* **Secure:** Executes commands directly without invoking a shell, preventing shell injection vulnerabilities.

## Example

The clitest.py code is tested by its own test specification:

```sh
$ python3 clitest.py clitest-*-tests.xml
TAP version 14
ok 1 - Should exit 0 and report a pass for a valid, passing suite
ok 2 - Should exit 1 and report a failure for a valid, failing suite
ok 3 - Should correctly process the 'normalize' attribute
ok 4 - Should correctly process the 'match=regex' attribute
ok 5 - Should correctly apply environment variables to subprocesses
ok 6 - Should fail gracefully if the suite file is not found
1..6
```

Refer to the [clitest-core-tests.xml](./clitest-core-tests.xml) file for an example.

## Installation

The `clitest.py` file is a standalone test runner. No dependencies need to be installed.

Just download the `clitest.py` code from the command line and begin using it right away:

```sh
$ curl -LJO https://raw.githubusercontent.com/bishopb/clitest/refs/heads/main/clitest.py
$ python3 clitest.py -h
```

## Usage

`clitest.py` is invoked from the command line, specifying one or more test suite files. By default, `clitest.py` will run the tests given in the test suite files. To simply list the cases that would be run, pass the --list-tests option.

```
usage: clitest.py [-h] [-v | -q | --list-tests] SUITE [SUITE ...]

A generic, language-agnostic command-line test runner.

positional arguments:
  SUITE          One or more paths to test suite XML files.

options:
  -h, --help     show this help message and exit
  -v, --verbose  Enable verbose output, printing descriptions and diagnostics.
  -q, --quiet    Enable quiet output, suppressing diagnostic messages on failure.
  --list-tests   List all tests that would be run without executing them.
```

## Test Suite XML Specification

A test suite file is an XML document that defines the tests to be run. Refer to the (clitest-schema.xsd)[./clitest-schema.xsd] file for the formal specification.

### Verifying a Test Suite

The `xmllint` tool can validate a test suite XML file you create against the clitest test suite XML schema definition, like so:

```sh
$ xmllint --noout --schema clitest-schema.xsd clitest-core-tests.xml
clitest-core-tests.xml validates
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
