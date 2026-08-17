-- 1. Criar o Banco de Dados
CREATE DATABASE IF NOT EXISTS optiorder;
USE optiorder;

-- 2. Tabela de Usuários (Representantes e Admins da Empresa)
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,
    tipo ENUM('representante', 'admin') NOT NULL DEFAULT 'representante',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Tabela de Óticas (Clientes)
CREATE TABLE IF NOT EXISTS oticas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    cnpj VARCHAR(18) NOT NULL UNIQUE,
    telefone VARCHAR(20),
    email VARCHAR(100),
    endereco TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Tabela de Marcas
CREATE TABLE IF NOT EXISTS marcas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(50) NOT NULL UNIQUE,
    status ENUM('ativa', 'inativa') DEFAULT 'ativa'
);

-- 5. Tabela de Produtos (Óculos)
CREATE TABLE IF NOT EXISTS produtos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(30) NOT NULL UNIQUE,
    modelo VARCHAR(100) NOT NULL,
    cor VARCHAR(50),
    tipo ENUM('solar', 'receituario') NOT NULL,
    preco DECIMAL(10, 2) NOT NULL,
    marca_id INT NOT NULL,
    FOREIGN KEY (marca_id) REFERENCES marcas(id) ON DELETE RESTRICT
);