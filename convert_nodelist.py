
import csv
import os
import argparse
import subprocess

# --- Main Conversion Logic ---
def convert_nodelist(input_file, output_file):
    if not os.path.exists(input_file):
        print("Error: {} not found.".format(input_file))
        return

    output_rows = []
    with open(input_file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader) # Skip header row

        try:
            ip_idx = header.index('ip address')
            host_idx = header.index('hostname')
            vend_idx = header.index('vender:cisco_xe,cisco_xr,juniper,nokia,arrcus,server')
            tty_idx = header.index('tty type:telnet ssh')
            user_idx = header.index('unique ID')
            pass_idx = header.index('unique password')
        except ValueError as e:
            print("Error: Missing expected column in {}: {}".format(input_file, e))
            return

        for row in reader:
            ip_address = row[ip_idx]
            hostname = row[host_idx]
            protocol = row[tty_idx]
            
            username = row[user_idx].strip()
            if not username:
                username = 'default'

            prompts = []
            password = row[pass_idx].strip()
            if not password:
                password = 'default'
            prompts.extend(["assword:", password])

            vendor = row[vend_idx]
            if vendor == 'cisco_xr':
                prompts.extend(["#", "terminal length 0"])
            elif vendor == 'juniper':
                prompts.extend([">", "set cli screen-length 0"])
            elif vendor == 'nokia':
                prompts.extend(["#", "environment more false"])

            output_row = [hostname, ip_address, username, protocol] + prompts
            output_rows.append(output_row)

    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(output_rows)
    
    print("Successfully converted {} to {}".format(input_file, output_file))

# --- SCP File Transfer Logic ---
def fetch_remote_file(host, user, password, remote_path, local_path):
    """Fetch a remote file using scp with sshpass."""
    local_file_path = os.path.join(local_path, os.path.basename(remote_path))
    command = [
        'sshpass', '-p', password, 
        'scp', '-o', 'StrictHostKeyChecking=no', 
        '{}@{}:{}'.format(user, host, remote_path), 
        local_path
    ]
    
    try:
        print("Fetching remote file...")
        subprocess.run(command, check=True, capture_output=True, text=True)
        print("Successfully fetched {} to {}".format(remote_path, local_path))
        return local_file_path
    except subprocess.CalledProcessError as e:
        print("Error during scp: {}".format(e.stderr))
        return None
    except FileNotFoundError:
        print("Error: sshpass is not installed. Please install it to use this feature.")
        return None

# --- Main Execution Block ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and convert a remote NodeList.csv file.")
    parser.add_argument('--host', required=True, help='IP address of the remote server.')
    parser.add_argument('--user', required=True, help='Username for the remote server.')
    parser.add_argument('--password', required=True, help='Password for the remote server.')
    parser.add_argument('--remote-path', required=True, help='Full path to NodeList.csv on the remote server.')
    parser.add_argument('--local-path', default='.', help='Local directory to save the files.')

    args = parser.parse_args()

    # 1. Fetch the remote file
    fetched_file = fetch_remote_file(args.host, args.user, args.password, args.remote_path, args.local_path)

    # 2. If fetch was successful, convert it
    if fetched_file:
        output_file = os.path.join(args.local_path, 'hosts_local.csv')
        convert_nodelist(fetched_file, output_file)
