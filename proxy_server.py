"""
Local SOCKS5 proxy server for routing Telegram API requests through VPN.

This proxy listens locally and routes all traffic through your VPN connection.
"""

import asyncio
import socket
import struct
from typing import Optional
import sys

# Try to import socks support
try:
    import socks
    SOCKS_AVAILABLE = True
except ImportError:
    SOCKS_AVAILABLE = False
    print("Warning: PySocks not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pysocks"])
    import socks
    SOCKS_AVAILABLE = True


class SOCKS5Proxy:
    """Simple SOCKS5 proxy server."""
    
    def __init__(self, listen_port: int = 1080):
        self.listen_port = listen_port
        self.server_socket = None
    
    async def handle_client(self, client_socket: socket.socket):
        """Handle a client connection."""
        try:
            # Set socket to blocking for initial handshake
            client_socket.setblocking(True)
            
            # SOCKS5 handshake
            data = client_socket.recv(1024)
            if not data or data[0] != 0x05:  # SOCKS5
                client_socket.close()
                return
            
            # Send authentication method (no auth)
            client_socket.sendall(b'\x05\x00')
            
            # Receive connection request
            data = client_socket.recv(1024)
            if not data or len(data) < 7:
                client_socket.close()
                return
            
            cmd = data[1]
            if cmd != 0x01:  # CONNECT
                client_socket.close()
                return
            
            # Parse address
            addr_type = data[3]
            if addr_type == 0x01:  # IPv4
                addr = socket.inet_ntoa(data[4:8])
                port = struct.unpack('>H', data[8:10])[0]
            elif addr_type == 0x03:  # Domain
                addr_len = data[4]
                addr = data[5:5+addr_len].decode('utf-8')
                port = struct.unpack('>H', data[5+addr_len:7+addr_len])[0]
            else:
                client_socket.close()
                return
            
            # Connect to target through system (which uses VPN)
            try:
                target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                target_socket.setblocking(True)
                target_socket.settimeout(10)  # 10 second timeout
                target_socket.connect((addr, port))
                
                # Send success response
                response = b'\x05\x00\x00\x01'
                # Get local IP for response
                try:
                    local_ip = socket.inet_aton(addr) if addr_type == 0x01 else socket.inet_aton('127.0.0.1')
                except:
                    local_ip = socket.inet_aton('127.0.0.1')
                response += local_ip
                response += struct.pack('>H', port)
                client_socket.sendall(response)
                
                # Set both sockets to non-blocking for relay
                client_socket.setblocking(False)
                target_socket.setblocking(False)
                
                # Relay data
                await self.relay_data(client_socket, target_socket)
                
            except socket.timeout:
                print(f"Timeout connecting to {addr}:{port}")
                client_socket.sendall(b'\x05\x04\x00\x01\x00\x00\x00\x00\x00\x00')
                client_socket.close()
            except Exception as e:
                print(f"Error connecting to {addr}:{port}: {e}")
                # Send failure response
                try:
                    client_socket.sendall(b'\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00')
                except:
                    pass
                client_socket.close()
                
        except Exception as e:
            print(f"Error handling client: {e}")
            try:
                client_socket.close()
            except:
                pass
    
    async def relay_data(self, client: socket.socket, target: socket.socket):
        """Relay data between client and target."""
        try:
            loop = asyncio.get_event_loop()
            
            async def read_from_socket(sock, name):
                """Read from socket with proper error handling."""
                while True:
                    try:
                        data = await loop.sock_recv(sock, 4096)
                        if not data:
                            return None
                        return data
                    except (socket.error, OSError) as e:
                        if e.errno in (10035, 11):  # EAGAIN/EWOULDBLOCK
                            await asyncio.sleep(0.01)
                            continue
                        return None
            
            async def write_to_socket(sock, data, name):
                """Write to socket with proper error handling."""
                try:
                    await loop.sock_sendall(sock, data)
                    return True
                except (socket.error, OSError):
                    return False
            
            # Relay in both directions
            while True:
                # Check both sockets for data
                tasks = [
                    asyncio.create_task(read_from_socket(client, "client")),
                    asyncio.create_task(read_from_socket(target, "target"))
                ]
                
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                
                # Cancel pending tasks
                for task in pending:
                    task.cancel()
                
                # Process completed reads
                for task in done:
                    try:
                        data = await task
                        if data is None:
                            # Connection closed
                            return
                        
                        # Determine which socket sent data
                        if task == tasks[0]:  # Client sent data
                            if not await write_to_socket(target, data, "target"):
                                return
                        else:  # Target sent data
                            if not await write_to_socket(client, data, "client"):
                                return
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        print(f"Relay error: {e}")
                        return
                
                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.001)
                
        except Exception as e:
            print(f"Relay error: {e}")
        finally:
            try:
                client.close()
            except:
                pass
            try:
                target.close()
            except:
                pass
    
    async def start(self):
        """Start the proxy server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('127.0.0.1', self.listen_port))
        self.server_socket.listen(10)
        self.server_socket.setblocking(False)
        
        print(f"✅ Proxy server started on 127.0.0.1:{self.listen_port}")
        print("   This proxy routes traffic through your VPN connection")
        print("   Press Ctrl+C to stop")
        print()
        
        loop = asyncio.get_event_loop()
        
        while True:
            try:
                client_socket, addr = await loop.sock_accept(self.server_socket)
                # Handle client in background task
                asyncio.create_task(self.handle_client(client_socket))
            except asyncio.CancelledError:
                break
            except Exception as e:
                if "10035" not in str(e):  # Ignore Windows non-blocking errors
                    print(f"Error accepting connection: {e}")
                await asyncio.sleep(0.1)


async def main():
    """Main function."""
    proxy = SOCKS5Proxy(listen_port=1080)
    try:
        await proxy.start()
    except KeyboardInterrupt:
        print("\n🛑 Stopping proxy server...")
    finally:
        if proxy.server_socket:
            proxy.server_socket.close()


if __name__ == "__main__":
    print("Starting local SOCKS5 proxy server...")
    print("Make sure your VPN is connected!")
    asyncio.run(main())

