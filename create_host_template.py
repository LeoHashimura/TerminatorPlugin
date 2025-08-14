
import pandas as pd

# Define the columns for the new host file
columns = [
    'hostname', 
    'ip_address', 
    'protocol', 
    'username', 
    'post_login_command', 
    'prompt_1', 
    'response_1', 
    'prompt_2', 
    'response_2',
    'prompt_3',
    'response_3'
]

# Create an empty DataFrame
df = pd.DataFrame(columns=columns)

# Add some example data to guide the user
example_data = [
    {
        'hostname': 'my-ssh-server', 
        'ip_address': '192.168.1.10', 
        'protocol': 'ssh', 
        'username': 'user1', 
        'prompt_1': 'assword:', 
        'response_1': 'ssh_password'
    },
    {
        'hostname': 'my-telnet-switch', 
        'ip_address': '192.168.1.11', 
        'protocol': 'telnet', 
        'prompt_1': 'Username:', 
        'response_1': 'admin', 
        'prompt_2': 'Password:', 
        'response_2': 'telnet_password'
    },
    {
        'hostname': 'my-console-server', 
        'ip_address': '192.168.1.12', 
        'protocol': 'telnet', 
        'username': 'console_user',
        'post_login_command': 'connect device-4', 
        'prompt_1': 'assword:', 
        'response_1': 'console_password'
    }
]

df = pd.concat([df, pd.DataFrame(example_data)], ignore_index=True)


# Define the output file name
output_file = 'hosts.xlsx'

# Create the Excel file
df.to_excel(output_file, index=False)

print(f"Successfully created host template: {output_file}")
