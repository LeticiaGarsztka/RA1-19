# Aluno 1: Função parseExpressao e Analisador Léxico com Autômato Finito Determinístico

# Implementação do analisador léxico usando Autômatos Finitos Determinísticos com cada estado como uma função.

# ====== TOKENS RECONHECIDOS ======
# LPAREN  -> (
# RPAREN  -> )
# NUMBER  -> inteiro ou real (ex: 3, 3.14)
# OP      -> +, -, *, /, //, %, ^
# KEYWORD -> RES
# MEMVAR  -> sequência de letras maiúsculas (ex: MEM, VAR, X)
# ============================================================

import sys
import json

# ====== DEFINIÇÃO DOS TIPOS DE TOKEN ======
TOKEN_LPAREN  = "LPAREN"
TOKEN_RPAREN  = "RPAREN"
TOKEN_NUMBER  = "NUMBER"
TOKEN_OP      = "OP"
TOKEN_KEYWORD = "KEYWORD"
TOKEN_MEMVAR  = "MEMVAR"
TOKEN_ERROR   = "ERROR" 

KEYWORD = {"RES"}

# ===== TOKEN: recebe tipo e valor =====
class Token:
    def __init___(self, tipo, valor):
        self.tipo = tipo
        self.valor = valor

    def __repr__(self):
        return f"Token({self.tipo}, {repr(self.valor)})"

    def to_dict(self):
        return{"tipo": self.tipo, "valor": self.valor}
        
# ===== MÉTODO: AUTÔMATO FINITO DETERMINÍSTICO =====
# Cada estado é uma função que recebe (texto, posição) e retorna (Token, nova_pos)
# ou (None, nova_pos) se não reconheceu nada (erro/espaço)

def _peek(texto, por):
    ''' Retorna o caractere na posição pos, ou None se fim do texto '''
    return texto[pos] if pos < len(texto) else None

# ===== Estado: espaços em branco (descartados) =====
def estado_espaco(texto, pos):
    '''Consome espaços/tabs e retorna None (nao gera token)'''
    if _peek(texto, pos) in (' ', '\t', '\r', '\n'):
        while pos < len(texto) and texto[pos] in (' ', '\t', '\r', '\n'):
            pos += 1
        return None, pos
    return False, pos # Falso: este estado não se aplica



# ===== Estado: parênteses esquerdo =====
def estado_lparen(texto, pos):
    if _peek(texto, pos) == '(':
        return Token(TOKEN_LPAREN, '('), pos + 1
    return False, pos


# ===== Estado: parênteses direito =====
def estado_rparen(texto, pos):
    if _peek(texto, pos) == ')':
        return Token(TOKEN_RPAREN, ')'), pos + 1
    return False, pos


# ---------------------------------------------------------------------------
# Estado: número (inteiro ou real, sinal negativo incluso)
# AFD:
#   q0 -> dígito -> q1 (acumulando inteiro)
#   q0 -> '-'    -> q_neg (sinal negativo)
#   q_neg -> dígito -> q1
#   q1 -> dígito -> q1
#   q1 -> '.'    -> q2 (ponto decimal)
#   q2 -> dígito -> q3 (parte fracionária)
#   q3 -> dígito -> q3
#   q2 -> não-dígito -> ERRO (ponto sem dígitos após)
#   Aceito em q1 (inteiro) e q3 (real)
# ---------------------------------------------------------------------------

def estado_numero(texto, pos):
    inicio = pos
    c = _peek

    #q0: inicio -> aceita dígito ou sinal negativo
    if c == '-':
        pos += 1
        c = _peek(texto, pos)
        if c is None or not c.isdigit():
            return False, inicio # não é número número, devolve

    if c is None or not c.isdigit():
        return False, inicio

    # q1: consumir dígitos inteiros
    while pos < len(texto) and texto[pos].isdigit():
        pos += 1

    # Verificar ponto duplo (ex: 3.14.5) -> ERRO
    if _peek(texto, pos) == '.':
        pos += 1 # consome primeiro ponto -> q2
        # q2 -> q3: precisa de ao menos um dígito
        if _peek(texto, pos) is None or not texto[pos].isdigit():
            lexema = texto[inicio:pos]
            return Token(TOKEN_ERROR, f"Número malformado: '{lexema}'"), pos
        
        while pos < len(texto) and texto[pos].isdigit():
            pos += 1
        
        # Segundo ponto -> ERRO
        if _peek(texto, pos) == '.':
            pos_err = pos
            while pos < len(texto) and texto[pos] not in (' ', '\t', ')', '(', '\n'):
                pos += 1
            lexema = texto[inicio:pos]
            return Token(TOKEN_ERROR, f"Número malformado: '{lexema}'"), pos

    # Verificar vírgula (separador inválido)
    if _peek(texto, pos) == ',':
        pos_err = pos
        while pos < len(texto) and texto[pos] not in (' ', '\t', ')', '(', '\n'):
            pos += 1
        lexema = texto[inicio: pos]
        return Token(TOKEN_ERROR, f"Número malformado (use ponto): '{lexema}'"), pos

    lexema = texto[inicio:pos]
    return Token(TOKEN_NUMBER, lexema), pos