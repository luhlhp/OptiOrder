import time
from typing import List
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
# --- PEDIDOS (AC2) ---
# ==========================================

# Schemas para o Pedido
class ItemPedidoSchema(BaseModel):
    produto_id: int
    quantidade: int
    preco_unitario: float

class CriarPedidoSchema(BaseModel):
    otica_id: int
    itens: List[ItemPedidoSchema]

# Rota para Criar/Finalizar o Pedido
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
        
        # 3. Salvar Pedido Principal
        query_pedido = """
            INSERT INTO pedidos (numero_pedido, otica_id, quantidade_total, valor_total)
            VALUES (%s, %s, %s, %s)
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

        # Rota para Listar todos os Pedidos Realizados
@app.get("/pedidos")
def listar_pedidos():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT p.id, p.numero_pedido, o.nome AS otica_nome, 
                   p.quantidade_total, p.valor_total, 
                   DATE_FORMAT(p.data_criacao, '%d/%m/%Y %H:%i') AS data_formatada
            FROM pedidos p
            INNER JOIN oticas o ON p.otica_id = o.id
            ORDER BY p.id DESC
        """
        cursor.execute(query)
        pedidos = cursor.fetchall()
        return pedidos
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
            SELECT i.id, prod.modelo, prod.marca, i.quantidade, i.preco_unitario, i.subtotal
            FROM itens_pedido i
            INNER JOIN produtos prod ON i.produto_id = prod.id
            WHERE i.pedido_id = %s
        """
        cursor.execute(query, (pedido_id,))
        itens = cursor.fetchall()
        return itens
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()