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

from matplotlib.pylab import rint

# ====== DEFINIÇÃO DOS TIPOS DE TOKEN ======
TOKEN_LPAREN  = "LPAREN"
TOKEN_RPAREN  = "RPAREN"
TOKEN_NUMBER  = "NUMBER"
TOKEN_OP      = "OP"
TOKEN_KEYWORD = "KEYWORD"
TOKEN_MEMVAR  = "MEMVAR"
TOKEN_ERROR   = "ERROR" 

KEYWORDS = {"RES"}

# ===== TOKEN: recebe tipo e valor =====
class Token:
    def __init__(self, tipo, valor):
        self.tipo = tipo
        self.valor = valor

    def __repr__(self):
        return f"Token({self.tipo}, {repr(self.valor)})"

    def to_dict(self):
        return{"tipo": self.tipo, "valor": self.valor}
        
# ===== MÉTODO: AUTÔMATO FINITO DETERMINÍSTICO =====
# Cada estado é uma função que recebe (texto, posição) e retorna (Token, nova_pos)
# ou (None, nova_pos) se não reconheceu nada (erro/espaço)

def _peek(texto, pos):
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
    c = _peek(texto, pos)
 
    # q0: início - aceita dígito ou sinal negativo
    if c == '-':
        pos += 1
        c = _peek(texto, pos)
        if c is None or not c.isdigit():
            return False, inicio   # não é número negativo, devolve
 
    if c is None or not c.isdigit():
        return False, inicio
 
    # q1: consumir dígitos inteiros
    while pos < len(texto) and texto[pos].isdigit():
        pos += 1
 
    # Verificar ponto duplo (ex: 3.14.5) -> ERRO
    if _peek(texto, pos) == '.':
        pos += 1  # consome primeiro ponto -> q2
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
        lexema = texto[inicio:pos]
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

# ===== MÉTODOS DE EXECUÇÃO DE TESTE =====
def _executar_teste(descricao, linha, espera_valido):
    ''' Método Auxiliar do Método executar_teste -> o compilador Python lê de cima para baixo '''
    tokens = []
    valido = parseExpressao(linha, tokens)
    status = 'OK' if valido == espera_valido else "FALHOU"
    print(f"   [{status}]  {descricao}")
    print(f"       Entrada : {repr(linha)}")
    print(f"       Tokens  : {tokens}")
    print(f"       Válido  : {valido}   (esperado:  {espera_valido})")
    print()
    return status == "OK"

def executar_testes():
    ''' Bateria de Testes do Analisador Léxico -> método principal '''
    print("="*60)
    print("TESTES DO ANALISADOR LÉXICO (AFD)")
    print("="*60)
    testes = [
        # (descrição, expressão, esperado_valido)
        # --- Entradas Válidas ---
        ("Adição simples",                  "(3.14 2.0 +)",        True),
        ("Subtração" ,                      "(10 3 -)",            True),
        ("Multiplicação de números reais",  "(1.5 2.5 *)",         True),
        ("Divisão de número reais",         "(9.0 3.0 /)",         True),
        ("Divisão de números inteiros",     "(10 3 //)",           True),
        ("Resto",                           "(10 3 %)",            True),
        ("Aninhada: soma de produtos",      "(A (C D *) +)",       True), # A, C, D são MENVAR válidos
        ("Aninhada válida",                 "((1.5 2.0 *) (3.0 4.0 *) /)", True),
        ("Comando RES",                     "(5 RES)",             True),
        ("Armazenar MEM",                   "(10.5 CONTADOR)",     True),
        ("Ler MEM",                         "(MEM)",               True),
        ("Número Negativo",                 "(-3.14 2.0 +)",       True),
        ("Número inteiro negativo",         "(-5 3 *)",            True),
        ("Expressão aninhada completa", "((2.0 3.0 +) (4.0 1.0 -) *)", True),

        # --- Entradas Inválidas ---
        ("Operador inválido &",             "(3.14 2.0 &)",           False),
        ("Número malformado 3.14.5",        "(3.14.5 2.0 +)",         False),
        ("Vírgula como separador",          "(3,14 2.0 +)",           False),
        ("Parêntese não fechado",           "(3 2 +",                 False),
        ("Parêntese extra fechado",         "(3 2 -))",               False),
        ("Parêntese não aberto",            "( 2 +)",                 False),
        ("Identificador inválido misto",    "(CONTADOR 2 +)",         False),
    ]

    aprovados = 0
    for desc, linha, esperado in testes:
        if _executar_teste(desc, linha, esperado):
            aprovados += 1

    print(f"Resultado: {aprovados}/{len(testes)} testes aprovados")
    print("=" * 60)
    return aprovados == len(testes)

# ===== Método de Salvar Tokens em Arquivo =====
def salvar_tokens(expressoes: list, nome_arquivo: str):
    ''' Salva as expressões em formato JSON -> pega o nome do arquivo e escreve as expressões em JSON'''
    with open(nome_arquivo, 'w', encoding='utf-8') as f:
        json.dump(expressoes, f, ensure_ascii=False, indent=2)
    print(f"Expressões salvas em: {nome_arquivo}")

def executarExpressao(expressoes: list):

    pilha = []
    instrucoes = []

    memoria_logica = []
    historico_operacoes = []

    for expressao in expressoes:
        instrucao = []
        
            
        for token in expressao:
            if token['tipo'] == TOKEN_NUMBER:
                pilha.append(token['valor'])
                instrucao.append(("PUSH", token['valor']))

            elif token['tipo'] == TOKEN_OP:
                op2 = pilha.pop()
                op1 = pilha.pop()
                pilha.append("TEMP")
                
                if token['valor'] == '+':
                    operacao = "ADD"
                elif token['valor'] == '-':
                    operacao = "SUB"
                elif token['valor'] == '*':
                    operacao = "MUL"
                elif token['valor'] == '/':
                    operacao = "DIV"
                elif token['valor'] == '//':
                    operacao = "IDIV"
                elif token['valor'] == '%':
                    operacao = "MOD"
                elif token['valor'] == '^':
                    operacao = "POW"

                instrucao.append((operacao,))

            elif token['tipo'] == TOKEN_MEMVAR:
                instrucao.append(("STORE", token['valor']))
    
            
            elif token['tipo'] == TOKEN_KEYWORD and token['valor'] == 'RES':
                if pilha:
                    pop = instrucao.pop()
                instrucao.append(("RES", f"{pop[1]}"))

            
        instrucoes.append(instrucao)

       
    print(instrucoes)
            
# ===== MAIN =====
def main():
    print("main")
    if len(sys.argv) < 2:
        print("Uso: python analisador_lexico.py <arquivo.txt>")
        print("     python analisador_lexico.py --testes")
        sys.exit(1)

    if sys.argv[1] == "--testes":
        sucesso = executar_testes()
        sys.exit(0 if sucesso else 1)

    nome_arquivo = sys.argv[1]

    try:
        with open(nome_arquivo, 'r', encoding='utf-8') as f:
            linhas = f.readlines()
    except FileNotFoundError:
        print(f"Erro: arquivo '{nome_arquivo}' não encontrado.")
        sys.exit(1)

    print(f"\nAnalisando: {nome_arquivo}")
    print("="*60)

    expressoes = []
    tem_erros = False

    for numero, linha in enumerate(linhas, 1):
        linha = linha.strip()
        if not linha or linha.startswith('#'):
            continue    # pulia linhas vazias e comentários

        tokens_linha = []
        valido = parseExpressao(linha, tokens_linha)
        print(f"Linha {numero:2d} : {linha}")
        for t in tokens_linha:
            marcador = " *** ERRO ***" if t.tipo == TOKEN_ERROR else ""
            print(f"            {t}{marcador}")
        print(f"        Válida: {"Sim" if valido else "Não"}")
        print()

        if valido:
            expressoes.append([
                t.to_dict() for t in tokens_linha
            ])
        else:
            tem_erros = True

    # Salvar tokens em arquivo
    base = nome_arquivo.rsplit('.', 1)[0]
    salvar_tokens(expressoes, base + "_tokens.json")

    print("=" * 60)
    if tem_erros:
        print("AVISO: foram encontrados erros léxicos.")
    else:
        print("Análise concluída sem erros.")

    executarExpressao(expressoes)

    sys.exit(1 if tem_erros else 0)

if __name__ == "__main__":
    main()
