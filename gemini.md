
# Gemini Plugin Development Plan

This document outlines the future development plan for the `multi_ssh.py` Terminator plugin.

## Phase 1: Python 3 and Terminator 2.1.3+ Compatibility

The first priority is to ensure the plugin is fully compatible with modern environments.

-   **Action:** Refactor the entire script to use modern Python 3 syntax (f-strings, etc.) and remove any Python 2 compatibility shims.
-   **Action:** Test against Terminator 2.1.3 to ensure all GTK and API calls are current.

## Phase 2: Adding Telnet and Console Server Support

This phase will extend the plugin's functionality beyond SSH.

### Protocol Handling

-   A new `protocol` column will be added to the `hosts.csv` (or its replacement). This column will specify whether the connection should use `ssh`, `telnet`, or `console`.
-   The `_login_to_host` function will be updated to read this protocol and construct the appropriate command (`ssh user@host`, `telnet host`, etc.).

### Console Server Logic

-   Connecting to a console server typically involves an extra step: after the initial connection, you often need to enter a port number or a specific command to reach the end device.
-   To handle this, we will introduce a new "post-login command" field in the host configuration. This will allow users to specify a command that should be sent after the initial prompt is detected.

## Phase 3: New Host File Format (`hosts.xlsx`)

To support these new features, the `hosts.csv` file will be replaced with a more structured Excel file (`hosts.xlsx`), managed by the `pandas` library.

### New `hosts.xlsx` Structure

The new Excel file will have the following columns:

| hostname | ip_address | protocol | username | post_login_command | prompt_1 | response_1 | prompt_2 | response_2 | ... |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| my-server | 1.2.3.4 | ssh | my-user | | assword: | mypass | | | |
| my-switch | 1.2.3.5 | telnet | | | sername: | admin | assword: | switchpass | |
| console-serv | 1.2.3.6 | telnet | | | login: | console-user | assword: | console-pass | connect-device-3 |

-   **`post_login_command`:** A command to be sent after the final password prompt.
-   **Flexible Prompts:** The `prompt_n`/`response_n` columns allow for a variable number of authentication steps.

### Implementation

-   The `_read_hosts_from_csv` function will be replaced with a `_read_hosts_from_excel` function that uses `pandas` to read the new file.
-   A separate Python script will be provided to generate a template `hosts.xlsx` file, making it easy for users to get started.

This plan will be implemented incrementally, starting with the Python 3 refactoring.
