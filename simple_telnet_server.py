

import asyncio

async def handle_client(reader, writer):
    peername = writer.get_extra_info('peername')
    print(f"Received connection from {peername}")

    # Use bytes for network communication
    writer.write(b"Welcome to the Test Telnet Server!\n")
    await writer.drain()

    # --- Login Prompt 1: Username ---
    writer.write(b"Username: ")
    await writer.drain()
    data = await reader.read(100)
    username = data.decode().strip()

    # --- Login Prompt 2: Password ---
    writer.write(b"Password: ")
    await writer.drain()
    data = await reader.read(100)
    password = data.decode().strip()

    # --- Authentication Check ---
    if username == 'admin' and password == 'testpass':
        writer.write(b"\nLogin successful!\n")
        writer.write(b"[mock-shell]# ")
        await writer.drain()

        # --- Mock Shell Loop ---
        while True:
            data = await reader.read(100)
            if not data:
                break
            command = data.decode().strip()
            if command == 'exit':
                break
            
            # Echo the command back
            writer.write(f"Command received: {command}\n".encode())
            writer.write(b"[mock-shell]# ")
            await writer.drain()
    else:
        writer.write(b"\nLogin failed.\n")
        await writer.drain()

    print(f"Closing connection from {peername}")
    writer.close()
    await writer.wait_closed()

async def main():
    server = await asyncio.start_server(
        handle_client, '0.0.0.0', 8023)

    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    print("Starting simple telnet server on port 8023...")
    print("Use Ctrl+C to stop.")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped.")

