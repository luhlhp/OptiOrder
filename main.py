import time
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from database import get_connection

app = FastAPI(title="OptiOrder API")

# LIBERAÇÃO DO CORS (Permite que o HTML/JS converse com o Python)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SCHEMAS DE VALIDAÇÃO ---
class LoginSchema(BaseModel):
    email: str
    senha: str

class OticaSchema(BaseModel):
    nome: str
    cnpj: str
    telefone: str | None = None
    email: str | None = None

class MarcaSchema(BaseModel):
    nome: str

class ProdutoSchema(BaseModel):
    codigo: str
    modelo: str
    cor: str
    tipo: str  # 'solar' ou 'receituario'
    preco: float
    marca_id: int

class UsuarioSchema(BaseModel):
    nome: str
    email: str
    senha: str

class StatusUpdateSchema(BaseModel):
    novo_status: str


# --- LOGIN ---
@app.post("/login")
def login(dados: LoginSchema):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, nome, email, tipo FROM usuarios WHERE email = %s AND senha = %s", (dados.email, dados.senha))
    usuario = cursor.fetchone()
    cursor.close()
    conn.close()
    if not usuario:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    return {"status": "sucesso", "usuario": usuario}


# --- USUÁRIOS ---
@app.get("/usuarios")
def listar_usuarios():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, nome, email FROM usuarios")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

@app.post("/usuarios")
def cadastrar_usuario(usuario: UsuarioSchema):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM usuarios WHERE email = %s", (usuario.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="E-mail já cadastrado!")

        query = "INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)"
        cursor.execute(query, (usuario.nome, usuario.email, usuario.senha))
        conn.commit()
        return {"mensagem": "Usuário cadastrado com sucesso!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# --- ÓTICAS ---
@app.get("/oticas")
def listar_oticas():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM oticas")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

@app.post("/oticas")
def cadastrar_otica(otica: OticaSchema):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = "INSERT INTO oticas (nome, cnpj, telefone, email) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (otica.nome, otica.cnpj, otica.telefone, otica.email))
        conn.commit()
        nova_id = cursor.lastrowid
        return {"mensagem": "Ótica cadastrada com sucesso!", "id": nova_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# --- MARCAS ---
@app.get("/marcas")
def listar_marcas():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM marcas")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

@app.post("/marcas")
def cadastrar_marca(marca: MarcaSchema):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = "INSERT INTO marcas (nome) VALUES (%s)"
        cursor.execute(query, (marca.nome,))
        conn.commit()
        nova_id = cursor.lastrowid
        return {"mensagem": "Marca cadastrada!", "id": nova_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# --- PRODUTOS ---
@app.get("/produtos")
def listar_produtos():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT p.id, p.codigo, p.modelo, p.cor, p.tipo, p.preco, m.nome AS marca 
            FROM produtos p 
            LEFT JOIN marcas m ON p.marca_id = m.id
        """
        cursor.execute(query)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

@app.post("/produtos")
def cadastrar_produto(dados: ProdutoSchema):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = """
            INSERT INTO produtos (codigo, modelo, cor, tipo, preco, marca_id) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (dados.codigo, dados.modelo, dados.cor, dados.tipo, dados.preco, dados.marca_id))
        conn.commit()
        return {"mensagem": "Produto cadastrado com sucesso!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# ==========================================
# --- PEDIDOS & GESTÃO (AC2 e AC3) ---
# ==========================================

class ItemPedidoSchema(BaseModel):
    produto_id: int
    quantidade: int
    preco_unitario: float

class CriarPedidoSchema(BaseModel):
    otica_id: int
    itens: List[ItemPedidoSchema]


# Rota para Criar/Finalizar o Pedido (AC2)
@app.post("/pedidos")
def criar_pedido(dados: CriarPedidoSchema):
    if not dados.itens:
        raise HTTPException(status_code=400, detail="O pedido deve conter pelo menos um produto.")

    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Gerar número do pedido único ex: ORD-171829102
        numero_pedido = f"ORD-{int(time.time())}"
        
        # 2. Calcular Totais
        qtd_total = sum(item.quantidade for item in dados.itens)
        valor_total = sum(item.quantidade * item.preco_unitario for item in dados.itens)
        
        # 3. Salvar Pedido Principal (Status inicial 'Pendente')
        query_pedido = """
            INSERT INTO pedidos (numero_pedido, otica_id, quantidade_total, valor_total, status)
            VALUES (%s, %s, %s, %s, 'Pendente')
        """
        cursor.execute(query_pedido, (numero_pedido, dados.otica_id, qtd_total, valor_total))
        pedido_id = cursor.lastrowid
        
        # 4. Salvar os Itens do Pedido
        query_item = """
            INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
            VALUES (%s, %s, %s, %s, %s)
        """
        for item in dados.itens:
            subtotal = item.quantidade * item.preco_unitario
            cursor.execute(query_item, (pedido_id, item.produto_id, item.quantidade, item.preco_unitario, subtotal))
            
        conn.commit()
        return {
            "status": "sucesso",
            "mensagem": "Pedido finalizado com sucesso!",
            "numero_pedido": numero_pedido,
            "pedido_id": pedido_id
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# Rota para Listar todos os Pedidos com Filtros Opcionais (AC3)
@app.get("/pedidos")
def listar_pedidos(
    busca: Optional[str] = None,
    status: Optional[str] = None,
    otica_id: Optional[int] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT p.id, p.numero_pedido, o.nome AS otica_nome, 
                   p.quantidade_total, p.valor_total, p.status,
                   DATE_FORMAT(p.data_criacao, '%d/%m/%Y %H:%i') AS data_formatada
            FROM pedidos p
            INNER JOIN oticas o ON p.otica_id = o.id
            WHERE 1=1
        """
        params = []

        if busca:
            query += " AND (p.numero_pedido LIKE %s OR o.nome LIKE %s)"
            params.extend([f"%{busca}%", f"%{busca}%"])
        
        if status:
            query += " AND p.status = %s"
            params.append(status)
            
        if otica_id:
            query += " AND p.otica_id = %s"
            params.append(otica_id)
            
        if data_inicio:
            query += " AND DATE(p.data_criacao) >= %s"
            params.append(data_inicio)
            
        if data_fim:
            query += " AND DATE(p.data_criacao) <= %s"
            params.append(data_fim)

        query += " ORDER BY p.id DESC"
        cursor.execute(query, tuple(params))
        return cursor.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# Rota para Listar os itens de um Pedido específico
@app.get("/pedidos/{pedido_id}/itens")
def listar_itens_pedido(pedido_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT i.id, prod.modelo, m.nome AS marca, i.quantidade, i.preco_unitario, i.subtotal
            FROM itens_pedido i
            INNER JOIN produtos prod ON i.produto_id = prod.id
            LEFT JOIN marcas m ON prod.marca_id = m.id
            WHERE i.pedido_id = %s
        """
        cursor.execute(query, (pedido_id,))
        return cursor.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# Rota para Alterar o Status e Salvar no Histórico (AC3)
@app.put("/pedidos/{pedido_id}/status")
def alterar_status_pedido(pedido_id: int, dados: StatusUpdateSchema):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. Busca o status atual do pedido
        cursor.execute("SELECT status FROM pedidos WHERE id = %s", (pedido_id,))
        pedido = cursor.fetchone()
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido não encontrado")
        
        status_anterior = pedido.get('status') or 'Pendente'
        novo_status = dados.novo_status

        # Se for o mesmo status, não grava histórico repetido
        if status_anterior == novo_status:
            return {"mensagem": "O pedido já está com este status"}

        # 2. Atualiza a coluna status na tabela 'pedidos'
        cursor.execute("UPDATE pedidos SET status = %s WHERE id = %s", (novo_status, pedido_id))

        # 3. Insere o registro na tabela 'historico_status'
        query_hist = """
            INSERT INTO historico_status (pedido_id, status_anterior, status_novo) 
            VALUES (%s, %s, %s)
        """
        cursor.execute(query_hist, (pedido_id, status_anterior, novo_status))

        # 4. Confirma as alterações no Banco de Dados
        conn.commit()
        
        return {"status": "sucesso", "mensagem": "Status e histórico atualizados!"}
    except Exception as e:
        conn.rollback()
        print(f"ERRO AO GRAVAR HISTÓRICO: {e}") # Exibe o erro no terminal
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# Rota para Consultar o Histórico de um Pedido (AC3)
@app.get("/pedidos/{pedido_id}/historico")
def obter_historico_pedido(pedido_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT 
                id,
                status_anterior,
                status_novo,
                DATE_FORMAT(data_alteracao, '%d/%m/%Y %H:%i') as data_formatada
            FROM historico_status
            WHERE pedido_id = %s
            ORDER BY data_alteracao DESC
        """
        cursor.execute(query, (pedido_id,))
        historico = cursor.fetchall()
        return historico
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()