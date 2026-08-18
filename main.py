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

# Schemas de validação de dados recebidos
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
    tipo: str
    preco: float
    marca_id: int

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

# --- ÓTICAS ---
@app.get("/oticas")
def listar_oticas():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM oticas")
    oticas = cursor.fetchall()
    cursor.close()
    conn.close()
    return oticas

@app.post("/oticas")
def cadastrar_otica(otica: OticaSchema):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO oticas (nome, cnpj, telefone, email) VALUES (%s, %s, %s, %s)", 
                   (otica.nome, otica.cnpj, otica.telefone, otica.email))
    conn.commit()
    nova_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return {"mensagem": "Ótica cadastrada!", "id": nova_id}

# --- MARCAS ---
@app.get("/marcas")
def listar_marcas():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM marcas")
    marcas = cursor.fetchall()
    cursor.close()
    conn.close()
    return marcas

@app.post("/marcas")
def cadastrar_marca(marca: MarcaSchema):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO marcas (nome) VALUES (%s)", (marca.nome,))
    conn.commit()
    nova_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return {"mensagem": "Marca cadastrada!", "id": nova_id}

# --- PRODUTOS ---
@app.get("/produtos")
def listar_produtos():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT p.*, m.nome as marca FROM produtos p JOIN marcas m ON p.marca_id = m.id")
    produtos = cursor.fetchall()
    cursor.close()
    conn.close()
    return produtos

@app.post("/produtos")
def cadastrar_produto(produto: ProdutoSchema):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO produtos (codigo, modelo, cor, tipo, preco, marca_id) VALUES (%s, %s, %s, %s, %s, %s)",
                   (produto.codigo, produto.modelo, produto.cor, produto.tipo, produto.preco, produto.marca_id))
    conn.commit()
    nova_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return {"mensagem": "Produto cadastrado!", "id": nova_id}

# Schema para receber os dados do novo usuário
class UsuarioSchema(BaseModel):
    nome: str
    email: str
    senha: str

@app.post("/usuarios")
def cadastrar_usuario(usuario: UsuarioSchema):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Verifica se o e-mail já está cadastrado
        cursor.execute("SELECT id FROM usuarios WHERE email = %s", (usuario.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="E-mail já cadastrado!")

        # Insere o novo usuário no banco
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

# Schema para receber os dados do produto
class ProdutoSchema(BaseModel):
    codigo: str
    modelo: str
    cor: str
    tipo: str  # 'solar' ou 'receituario'
    preco: float
    marca_id: int

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