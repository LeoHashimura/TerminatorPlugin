
import pandas as pd
import csv
import os

# Define the input and output file names
csv_file = 'hosts.csv'
excel_file = 'hosts.xlsx'

# Define the columns for the new Excel file
excel_columns = [
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

# Check if the csv file exists
if not os.path.exists(csv_file):
    print("Error: hosts.csv not found. Cannot convert.")
else:
    # Read the data from the CSV file
    converted_data = []
    with open(csv_file, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 3:
                continue # Skip malformed rows
            
            new_row = {
                'hostname': row[0],
                'ip_address': row[1],
                'protocol': 'ssh', # Default to ssh for all old entries
                'username': row[2],
                'post_login_command': '' # Default to empty
            }

            # Map the prompts and responses
            prompt_index = 1
            for i in range(3, len(row), 2):
                if (i + 1) < len(row):
                    new_row['prompt_{}'.format(prompt_index)] = row[i]
                    new_row['response_{}'.format(prompt_index)] = row[i+1]
                    prompt_index += 1
            
            converted_data.append(new_row)

    # Create a pandas DataFrame
    df = pd.DataFrame(converted_data, columns=excel_columns)

    # Create the Excel file
    df.to_excel(excel_file, index=False)

    print("Successfully converted hosts.csv to hosts.xlsx")
