// cliente.js
const WebSocket = require('ws');

class BridgeClient {
    constructor() {
        this.ws = new WebSocket('ws://localhost:8765');
        this.funcoes_js = {};

        this.ws.on('open', () => {
            console.log('WebSocket connected to ws://localhost:8765');
        });

        this.ws.on('message', async (data) => {
            console.log('Received from server:', data.toString());
            let requisicao;
            try {
                requisicao = JSON.parse(data);
            } catch (err) {
                console.error('Invalid JSON from server:', err);
                return;
            }

            if (requisicao.tipo === 'call_js' && this.funcoes_js[requisicao.funcao]) {
                try {
                    const resultado = await this.funcoes_js[requisicao.funcao](...requisicao.args);
                    this.ws.send(JSON.stringify({ success: true, resultado }));
                } catch (err) {
                    this.ws.send(JSON.stringify({ success: false, error: err.message }));
                }
            } else {
                this.ws.send(JSON.stringify({ success: false, error: 'Function not found or invalid request' }));
            }
        });

        this.ws.on('error', (err) => {
            console.error('WebSocket error:', err.message);
        });

        this.ws.on('close', () => {
            console.log('WebSocket connection closed');
        });
    }

    registrar_funcao_js(nome, funcao) {
        this.funcoes_js[nome] = funcao;
    }
}

// Exemplo: funções JS para web services
const bridge = new BridgeClient();
bridge.registrar_funcao_js('fetch_from_api', async (endpoint) => {
    console.log('fetch_from_api called with:', endpoint);
    // Example response to make the demo work without external API dependency
    return {
        endpoint,
        data: {
            message: 'This is a stubbed response from fetch_from_api',
        },
    };
});