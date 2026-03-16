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

# ===== Método Estado Operador =====
'''
Esse método reconhece +, -, *, /, //, %, ^
OBS: '-' pode ser número negativo, a ordem de tentativa no despachante garante que o número é tentado ANTES do operador isolado.
'''
def estado_operador(texto, pos):
    c = _peek(texto, pos)
    if c == '+':
        return Token(TOKEN_OP, '+'), pos + 1

    if c == '-':
        return Token(TOKEN_OP, '-'), pos + 1

    if c == '*':
        return Token(TOKEN_OP, '*'), pos + 1

    if c == '/':
        pos += 1
        if _peek(texto, pos) == '/':
            return Token(TOKEN_OP, '//'), pos + 1
        return Token(TOKEN_OP, '/'), pos + 1

    if c == '%':
        return Token(TOKEN_OP, '%'), pos + 1
    
    if c == '^':
        return Token(TOKEN_OP, '^'), pos + 1
    return False, pos

# ===== Método Estado Identificador =====
''' Neste método verifica o token, reconhecendo a sequência de letras maiúsculas
AFD:
    q0 -> maiúscula -> q1
    q1 -> maiúscula -> q1
    q1 -> outro caractere da sequência -> aceita
O programa decide se é uma KEYWORD(RES) ou MEMVAR (variável de memória)
'''
def estado_identificador(texto, pos):
    c = _peek(texto, pos)
    if c is None or not c.isupper():
        return False, pos

    inicio = pos
    while pos < len(texto) and texto[pos].isupper():
        pos += 1

    # Verificar mistura inválida de maiúsculas/minúsculas/dígitos
    if pos < len(texto) and (texto[pos].islower() or texto[pos].isdigit()):
        while pos < len(texto) and texto[pos] not in (' ', '\t', ')', '(', '\n'):
            pos += 1
        lexema = texto[inicio:pos]
        return Token(TOKEN_ERROR, f"Identificador Inválido: '{lexema}'"), pos

    lexema = texto[inicio:pos]
    if lexema in KEYWORDS:
        return Token(TOKEN_KEYWORD, lexema), pos
    return Token(TOKEN_MEMVAR, lexema), pos

# ===== Método Estado Inválido =====
''' Estado caractere inválido: captura qualquer caractere não reconhecido'''
def estado_invalido(texto, pos):
    c = _peek(texto, pos)
    if c is not None:
        return Token(TOKEN_ERROR, f"Caractere Inválido: '{c}'"), pos + 1
    return False, pos
    
# ===== Método do Despachante DO AFD =====
'''Tenta cada estado na ordem definida '''
_ESTADOS = [
    estado_espaco,
    estado_lparen,
    estado_rparen,
    estado_numero,      # número antes de operador (para negativos)
    estado_operador,
    estado_identificador,
    estado_invalido,     # fallback; a vírgula serve para dar continuidade caso queira adicionar uma linha a mais
]

def _proximo_token(texto, pos):
    '''
    Executa o AFD: tenta cada estado e retorna (Token|None, nova_pos).
    Retorna (None, nova_pos) para espaços (token descartado).
    Retorna (Token, nova_pos) para qualquer outro reconhecimento.
    '''
    for estado in _ESTADOS:
        resultado, nova_pos = estado(texto, pos)
        if resultado is False:
            continue    # este estado não se aplica, tenta próximo 
        return resultado, nova_pos
    # Nunca deve chegar aqui (estado_invalido captura tudo)
    return Token(TOKEN_ERROR, f"Falha interna pos={c}"), pos + 1

# ===== Método parseExpressao  =====
def parseExpressao(linha: str, tokens_out: list) -> bool:
    '''
    Analisa uma linha de expressão RPN e extrai tokens via AFD.
    
    === PARÂMETROS ===
        - linha     : string com a expressão a analisar
        - tokens_out: lista que receberá os tokens encontrados (modificada in-place, ou seja, a mesma lista da memória)

    === RETORNA ===
        - True  : se todos os tokens são válidos
        - False : se algum token de erro foi encontrado
    '''
    pos = 0
    tem_erro = False
    while pos < len(linha):
        token, pos = _proximo_token(linha, pos)
        if token is None:
            continue    # espaço descartado
        tokens_out.append(token)
        if token.tipo == TOKEN_ERROR:
            tem_erro = True
    
    # Validação Extra: parênteses balanceados
    profundidade = 0
    for t in tokens_out:
        if t.tipo == TOKEN_LPAREN:
            profundidade += 1
        elif t.tipo == TOKEN_RPAREN:
            profundidade -= 1
            if profundidade < 0:
                tokens_out.append(Token(TOKEN_ERROR, "Parêntese ')' sem abertura"))
                tem_erro = True
                break

    if profundidade > 0:
        tokens_out.append(Token(TOKEN_ERROR, f"{profundidade} parêntese(s) '(' não fechados(s)"))
        tem_erro = True
    
    return not tem_erro


# ===== MAIN =====
def main():
    print("main")

if __name__ == "__main__":
    main()
