# cookiescript/database.py
import sqlite3
from typing import List, Dict, Any

class DatabaseOps:
    """Operações de banco de dados SQLite"""

    def __init__(self):
        self.connections = {}

    def conectar(self, caminho_db: str) -> str:
        """Conecta a um banco de dados SQLite"""
        if caminho_db not in self.connections:
            self.connections[caminho_db] = sqlite3.connect(caminho_db)
        return f"Conectado a {caminho_db}"

    def executar_query(self, caminho_db: str, query: str, params: List[Any] = None) -> List[Dict[str, Any]]:
        """Executa uma query SQL e retorna resultados"""
        if caminho_db not in self.connections:
            raise ValueError(f"Conexão não encontrada: {caminho_db}")

        conn = self.connections[caminho_db]
        cursor = conn.cursor()

        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if query.strip().upper().startswith('SELECT'):
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return results
            else:
                conn.commit()
                return [{"rows_affected": cursor.rowcount}]

        except Exception as e:
            return [{"error": str(e)}]

    def fechar_conexao(self, caminho_db: str) -> str:
        """Fecha conexão com banco de dados"""
        if caminho_db in self.connections:
            self.connections[caminho_db].close()
            del self.connections[caminho_db]
            return f"Conexão fechada: {caminho_db}"
        return f"Conexão não encontrada: {caminho_db}"