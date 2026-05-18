import asyncio
import websockets
import json

async def handler(websocket, path=None):
    print('Client connected')

    call = {
        'tipo': 'call_js',
        'funcao': 'fetch_from_api',
        'args': ['/data']
    }
    await websocket.send(json.dumps(call))

    async for message in websocket:
        print('Received from client:', message)
        try:
            resposta = json.loads(message)
            print('Parsed response:', resposta)
        except json.JSONDecodeError:
            print('Received invalid JSON from client')

async def main(port: int = 8765):
    try:
        async with websockets.serve(handler, 'localhost', port):
            print(f'WebSocket server listening on ws://localhost:{port}')
            await asyncio.Future()  # keep running
    except OSError as e:
        print(f'Erro ao abrir porta {port}: {e}')

if __name__ == '__main__':
    asyncio.run(main())
