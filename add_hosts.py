
import pandas as pd

# Define the file path
excel_file = 'hosts.xlsx'

# Create the new host data
new_hosts = [
    {
        'hostname': 'debian-ssh',
        'ip_address': '192.168.0.118',
        'protocol': 'ssh',
        'username': 'Leonard',
        'prompt_1': 'assword:', # Generic password prompt
        'response_1': 'NismoS13'
    },
    {
        'hostname': 'debian-telnet',
        'ip_address': '192.168.0.118',
        'protocol': 'telnet',
        'username': 'admin',
        'prompt_1': 'Username:',
        'response_1': 'admin',
        'prompt_2': 'Password:',
        'response_2': 'testpass'
    }
]

# Read the existing data
df = pd.read_excel(excel_file)

# Create a DataFrame for the new hosts
new_df = pd.DataFrame(new_hosts)

# Combine the old and new data
combined_df = pd.concat([df, new_df], ignore_index=True)

# Write the updated data back to the file
combined_df.to_excel(excel_file, index=False)

print(f"Successfully added new hosts to {excel_file}")
