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

## Usage

`clitest.py` is invoked from the command line, specifying one or more test suite files.

```
usage: clitest.py [-h] [-v | -q] SUITE [SUITE ...]

A generic, language-agnostic command-line test runner.

positional arguments:
  SUITE                 One or more paths to test suite XML files.

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Enable verbose output, printing descriptions from the
                        test suite as diagnostic comments.
  -q, --quiet           Enable quiet output.
```

## Test Suite XML Specification

A test suite file is an XML document that defines the tests to be run.

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
