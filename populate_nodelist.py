
import csv
import random
import string

# Define the output file
output_file = 'NodeList.csv'

# Define the data generation rules
first_names = ['james', 'mary', 'john', 'patricia', 'robert', 'jennifer', 'michael', 'linda', 'william', 'elizabeth']
last_names = ['smith', 'jones', 'williams', 'brown', 'davis', 'miller', 'wilson', 'moore', 'taylor', 'anderson']
vendors = ['cisco_xe', 'cisco_xr', 'nokia', 'server', 'arrcus']
protocols = ['ssh', 'telnet']

def generate_random_hostname():
    """Generate a random 14-character hostname."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits + '-', k=14))

def generate_random_password():
    """Generate a random 8-10 character password."""
    length = random.randint(8, 10)
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Generate the data
data_rows = []
for _ in range(20):
    ip_address = f"10.1.4.{random.randint(1, 254)}"
    hostname = generate_random_hostname()
    vendor = random.choice(vendors)
    
    protocol = random.choice(protocols)
    if vendor in ['nokia', 'arrcus', 'cisco_xr']:
        protocol = 'ssh'
        
    username = f"{random.choice(first_names)}.{random.choice(last_names)}"
    password = generate_random_password()
    show_command_count = random.randint(1, 9)
    clear_log = random.choice(['yes', ''])
    show_run = random.choice(['yes', ''])
    
    data_rows.append([
        ip_address,
        hostname,
        vendor,
        protocol,
        username,
        password,
        show_command_count,
        clear_log,
        show_run
    ])

# Write the data to the CSV file
with open(output_file, 'a', newline='') as f:
    writer = csv.writer(f)
    writer.writerows(data_rows)

print(f"Successfully added 20 random rows to {output_file}")
