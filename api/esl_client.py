import asyncio
import logging

logger = logging.getLogger(__name__)

class ESLClient:
    def __init__(self, host='127.0.0.1', port=8021, password='ClueCon'):
        self.host = host
        self.port = port
        self.password = password
        self.reader = None
        self.writer = None
        self.connected = False
        self._lock = asyncio.Lock()
        
    async def connect(self):
        """Establish a pure asyncio raw socket connection to FreeSWITCH ESL."""
        async with self._lock:
            if self.connected:
                return
            try:
                # Add a tiny sleep to allow FreeSWITCH to boot up if they are started simultaneously
                await asyncio.sleep(1)
                
                self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
                
                # ESL immediately sends "Content-Type: auth/request\n\n"
                auth_req = await self.reader.readuntil(b'\n\n')
                if b'auth/request' in auth_req:
                    # Send authentication password
                    self.writer.write(f"auth {self.password}\n\n".encode())
                    await self.writer.drain()
                    
                    auth_resp = await self.reader.readuntil(b'\n\n')
                    if b'+OK accepted' in auth_resp:
                        self.connected = True
                        logger.info(f"Successfully connected to FreeSWITCH ESL at {self.host}:{self.port}")
                    else:
                        raise Exception(f"ESL Auth failed. Response: {auth_resp}")
            except Exception as e:
                logger.error(f"Failed to connect to FreeSWITCH ESL: {e}")
                self.connected = False
            
    async def disconnect(self):
        async with self._lock:
            if self.writer:
                self.writer.write(b"exit\n\n")
                try:
                    await self.writer.drain()
                except:
                    pass
                self.writer.close()
                try:
                    await self.writer.wait_closed()
                except:
                    pass
            self.connected = False
            logger.info("Disconnected from FreeSWITCH ESL")
            
    async def originate(self, phone_number: str, extension: str = "ai_agent"):
        """
        Originates an outbound call via a SIP gateway.
        When answered, the call is transferred to the dialplan extension.
        """
        if not self.connected:
            await self.connect()
            if not self.connected:
                raise Exception("Could not connect to ESL to originate call")
                
        # Note: Replace 'my_provider' with your actual SIP gateway profile
        gateway_string = f"sofia/gateway/my_provider/{phone_number}"
        
        logger.info(f"Originating call to {phone_number} -> {extension}")
        
        async with self._lock:
            # bgapi executes the command asynchronously without blocking
            command = f"bgapi originate {gateway_string} {extension} XML default\n\n"
            self.writer.write(command.encode())
            await self.writer.drain()
            
            # Read the immediate Job-UUID response
            response = await self.reader.readuntil(b'\n\n')
            resp_str = response.decode().strip()
            logger.info(f"Originate response: {resp_str}")
            return resp_str

# Global instance
esl_client = ESLClient()
