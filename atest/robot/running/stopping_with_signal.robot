*** Settings ***
Documentation     Test that SIGINT and SIGTERM can stop execution gracefully
...               (one signal) and forcefully (two signals). Windows does not
...               support these signals so we use CTRL_C_EVENT instead SIGINT
...               and do not test with SIGTERM.
Resource          atest_resource.robot

*** Variables ***
${TEST FILE}      %{TEMPDIR}${/}signal-tests.txt

*** Test Cases ***
SIGINT Signal Should Stop Test Execution Gracefully
    Start And Send Signal    without_any_timeout.robot    One SIGINT
    Check Test Cases Have Failed Correctly

SIGTERM Signal Should Stop Test Execution Gracefully
    [Tags]    no-windows
    Start And Send Signal    without_any_timeout.robot    One SIGTERM
    Check Test Cases Have Failed Correctly

Execution Is Stopped Even If Keyword Swallows Exception
    Start And Send Signal    swallow_exception.robot    One SIGINT
    Check Test Cases Have Failed Correctly

One Signal Should Stop Test Execution Gracefully When Run Keyword Is Used
    Start And Send Signal    run_keyword.robot    One SIGINT
    Check Test Cases Have Failed Correctly

One Signal Should Stop Test Execution Gracefully When Test Timeout Is Used
    Start And Send Signal    test_timeout.robot    One SIGINT
    Check Test Cases Have Failed Correctly

One Signal Should Stop Test Execution Gracefully When Keyword Timeout Is Used
    Start And Send Signal    keyword_timeout.robot    One SIGINT
    Check Test Cases Have Failed Correctly

Two SIGINT Signals Should Stop Test Execution Forcefully
    Start And Send Signal    without_any_timeout.robot    Two SIGINTs    2s
    Check Tests Have Been Forced To Shutdown

Two SIGTERM Signals Should Stop Test Execution Forcefully
    [Tags]    no-windows
    Start And Send Signal    without_any_timeout.robot    Two SIGTERMs    2s
    Check Tests Have Been Forced To Shutdown

Two Signals Should Stop Test Execution Forcefully When Run Keyword Is Used
    Start And Send Signal    run_keyword.robot    Two SIGINTs    2s
    Check Tests Have Been Forced To Shutdown

Two Signals Should Stop Test Execution Forcefully When Test Timeout Is Used
    Start And Send Signal    test_timeout.robot    Two SIGINTs    2s
    Check Tests Have Been Forced To Shutdown

Two Signals Should Stop Test Execution Forcefully When Keyword Timeout Is Used
    Start And Send Signal    keyword_timeout.robot    Two SIGINTs    2s
    Check Tests Have Been Forced To Shutdown

One Signal Should Stop Test Execution Gracefully And Test Case And Suite Teardowns Should Be Run
    Start And Send Signal    with_teardown.robot    One SIGINT
    Check Test Cases Have Failed Correctly
    ${tc} =    Get Test Case    Test
    Check Log Message    ${tc.teardown[0]}          Logging Test Case Teardown
    Check Log Message    ${SUITE.teardown[0, 0]}    Logging Suite Teardown

Skip Teardowns After Stopping Gracefully
    Start And Send Signal    with_teardown.robot    One SIGINT    0s    --SkipTeardownOnExit
    Check Test Cases Have Failed Correctly
    ${tc} =    Get Test Case    Test
    Teardown Should Not Be Defined    ${tc}
    Teardown Should Not Be Defined    ${SUITE}

SIGINT Signal Should Stop Async Test Execution Gracefully
    Start And Send Signal    async_stop.robot    One SIGINT    5
    Check Test Cases Have Failed Correctly
    ${tc} =    Get Test Case    Test
    Length Should Be     ${tc[1].body}             1
    Check Log Message    ${tc[1, 0]}               Start Sleep
    Length Should Be     ${SUITE.teardown.body}    0

Two SIGINT Signals Should Stop Async Test Execution Forcefully
    Start And Send Signal    async_stop.robot    Two SIGINTs    5
    Check Tests Have Been Forced To Shutdown

SIGTERM Signal Should Stop Async Test Execution Gracefully
    [Tags]    no-windows
    Start And Send Signal    async_stop.robot    One SIGTERM    5
    Check Test Cases Have Failed Correctly
    ${tc} =    Get Test Case    Test
    Length Should Be     ${tc[1].body}             1
    Check Log Message    ${tc[1, 0]}               Start Sleep
    Length Should Be     ${SUITE.teardown.body}    0

Two SIGTERM Signals Should Stop Async Test Execution Forcefully
    [Tags]    no-windows
    Start And Send Signal    async_stop.robot    Two SIGTERMs    5
    Check Tests Have Been Forced To Shutdown

Signal handler is reset after execution
    [Tags]    no-windows
    ${result} =    Run Process
    ...    @{INTERPRETER.interpreter}
    ...    ${DATADIR}/running/stopping_with_signal/test_signalhandler_is_reset.py
    ...    stderr=STDOUT
    ...    env:PYTHONPATH=${INTERPRETER.src_dir}
    Log     ${result.stdout}
    Should Contain X Times    ${result.stdout}    Execution terminated by signal    count=1
    Should Be Equal    ${result.rc}    ${0}

*** Keywords ***
Start And Send Signal
    [Arguments]    ${datasource}    ${signals}    ${sleep}=0s    @{extra options}
    Remove File    ${TEST FILE}
    Start Run    ${datasource}    ${sleep}    @{extra options}
    Wait Until Created    ${TESTFILE}    timeout=45s
    Run Keyword    ${signals}
    ${result} =    Wait For Process    timeout=45s    on_timeout=terminate
    Log Many    ${result.rc}    ${result.stdout}    ${result.stderr}
    Set Test Variable    $STDERR    ${result.stderr}

Start Run
    [Arguments]    ${datasource}    ${sleep}    @{extra options}
    @{command} =    Create List
    ...    @{INTERPRETER.runner}
    ...    --output    ${OUTFILE}    --report    NONE    --log    NONE
    ...    --variable    TESTSIGNALFILE:${TEST FILE}
    ...    --variable    TEARDOWNSLEEP:${sleep}
    ...    --variablefile    ${CURDIR}${/}enable_ctrl_c_event.py
    ...    @{extra options}
    ...    ${DATADIR}${/}running${/}stopping_with_signal${/}${datasource}
    Log Many    @{command}
    Start Process    @{command}

Check Test Cases Have Failed Correctly
    Process Output    ${OUTFILE}
    Check Test Tags    Test
    Check Test Tags    Test2    robot:exit

Check Tests Have Been Forced To Shutdown
    Should Contain    ${STDERR}    Execution forcefully stopped

One SIGINT
    # Process library doesn't support sending signals on Windows so need to
    # use Call Method instead. Also use CTRL_C_EVENT, not SIGINT, on Windows.
    ${process} =    Get Process Object
    ${signal} =    Evaluate    signal.CTRL_C_EVENT if $INTERPRETER.is_windows else signal.SIGINT
    Call Method    ${process}    send_signal    ${signal}

One SIGTERM
    Send Signal To Process    SIGTERM

Two SIGINTs
    One SIGINT
    Sleep    1s
    One SIGINT

Two SIGTERMs
    One SIGTERM
    Sleep    1s
    One SIGTERM
