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
import os
from assembly import gerarAssembly, criarArquivoAssembly, lerArquivo

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

def executar_testes_aluno1():
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

def executar_testes_aluno4():
    '''
    Bateria de testes para validar exibirResultados e o fluxo completo.
    Cobre expressões simples, complexas, MEM e RES.
    '''

    print('='*60)
    print("TESTES DO ALUNO 4 - exibirResultados e fluxo completo")
    print('='*60)

    def _testar(descricao, linhas, esperados):
        expressoes = []
        for linha in linhas:
            tokens_linha = []
            if parseExpressao(linha, tokens_linha):
                expressoes.append([t.to_dict() for t in tokens_linha])

        historico, memoria = executarExpressao(expressoes, "_testes_aluno4.json")
        resultados = historico

        ok = True
        for i, (res, esp) in enumerate(zip(resultados, esperados)):
            # tolerância de 0.001 para floats
            if abs(res - esp) > 0.001:
                print(f"  [FALHOU]  {descricao} - expressão {i+1}: obteve {res}, esperava {esp}")
                ok = False

        if len(resultados) != len(esperados):
            print(f"  [FALHOU]  {descricao} - quantidade de resultados: {len(resultados)}, esperava {len(esperados)}")
            of = False

        if ok:
            print(f"  [OK]   {descricao}")

        exibirResultados(resultados)
        return ok
    
    testes = [
        (
            "Adição Simples",
            ["(3.0 2.0 +)"],
            [5.0]
        ),
        (
            "Subtração",
            ["(10 3 -)"],
            [7.0]
        ),
        (
            "Multiplicação Real",
            ["(1.5 2.0 *)"],
            [3.0]
        ),
        (
            "Divisão Real",
            ["(9.0 3.0 /)"],
            [3.0]
        ),
        (
            "Divisão Inteira",
            ["(10 3 //)"],
            [3.0]
        ),
        (
            "Resto",
            ["(10 3 %)"],
            [1.0]
        ),
        (
            "Potência",
            ["(2 3 ^)"],
            [8.0]
        ),
        (
            "Expressão Aninhada",
            ["((2.0 3.0 +) (4.0 1.0 -)*)"],
            [15.0]
        ),
        (
            "MEM: armazenar e ler",
            ["(42.0 MEM)", "(MEM)"],
            [42.0, 42.0]
        ),
        (
            "RES: recuperar resultado anterior",
            ["(3.0 2.0 +)", "(1 RES)"],
            [5.0, 5.0]
        ),
        (
            "Número Negativo",
            ["(-3.0 2.0 +)"],
            [-1.0]
        ),
        (
            "Variável de Memória Personalizada",
            ["(10.0 SOMA)", "(SOMA)"],
            [10.0, 10.0]
        ),
    ]

    aprovados = sum(1 for desc, linhas, esp in testes if _testar(desc, linhas, esp))
    print(f"\nResultado: {aprovados}/{len(testes)} testes aprovados")
    print("=" * 60)
    return aprovados == len(testes)
    
# ===== Método de Salvar Tokens em Arquivo =====
def salvar_tokens(expressoes: list, nome_arquivo: str):
    ''' Salva as expressões em formato JSON -> pega o nome do arquivo e escreve as expressões em JSON'''
    with open(nome_arquivo, 'w', encoding='utf-8') as f:
        json.dump(expressoes, f, ensure_ascii=False, indent=2)
    print(f"Expressões salvas em: {nome_arquivo}")

def executarExpressao(expressoes: list, nome_arq="instrucoes.json"):
    instrucoes_totais = []
    memoria = {}
    historico = []

    def avaliar_expressao(tokens):
        instrucoes = []
        pilha_vals = []
        pilha_instr = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            tipo = token['tipo']
            valor = token['valor']

            if tipo in (TOKEN_LPAREN, TOKEN_RPAREN):
                i += 1
                continue

            if tipo == TOKEN_NUMBER:
                v = float(valor)
                pilha_vals.append(v)
                pilha_instr.append(valor)
                instrucoes.append(("PUSH", valor))

            elif tipo == TOKEN_OP:
                if len(pilha_vals) < 2:
                    i += 1
                    continue

                op2_v = pilha_vals.pop()
                op1_v = pilha_vals.pop()
                pilha_instr.pop()
                pilha_instr.pop()

                op_map = {
                    '+':  ("ADD", lambda a, b: a + b),
                    '-':  ("SUB", lambda a, b: a - b),
                    '*':  ("MUL", lambda a, b: a * b),
                    '/':  ("DIV", lambda a, b: a / b),
                    '//': ("IDIV", lambda a, b: float(int(a) // int(b))),
                    '%':  ("MOD", lambda a, b: float(int(a) % int(b))),
                    '^':  ("POW", lambda a, b: a ** b),
                }
                nome_op, func_op = op_map[valor]
                resultado = func_op(op1_v, op2_v)
                pilha_vals.append(resultado)
                pilha_instr.append("TEMP")
                instrucoes.append((nome_op,))

            elif tipo == TOKEN_MEMVAR:
                if valor == "MEM":
                    if "MEM" in memoria:
                        v = memoria["MEM"]
                        pilha_vals.append(v)
                        pilha_instr.append("MEM")
                        instrucoes.append(("LOAD", "MEM"))

                else:
                    if pilha_vals:
                        v = pilha_vals.pop()
                        pilha_instr.pop()
                        memoria[valor] = v
                        instrucoes.append(("STORE", valor))
                    elif valor in memoria:
                        v = memoria[valor]
                        pilha_vals.append(v)
                        pilha_instr.append(valor)
                        instrucoes.append(("LOAD", valor))

            elif tipo == TOKEN_KEYWORD and valor == "RES":
                if pilha_vals: 
                    n = int(pilha_vals.pop())
                    pilha_instr.pop()
                    idx = len(historico) - n
                    if 0 <= idx < len(historico):
                        v = historico[idx]
                        pilha_vals.append(v)
                        pilha_instr.append("RES_RESULT")
                        instrucoes.append(("RES", str(n)))

            i += 1

        resultado_final = pilha_vals[-1] if pilha_vals else None
        return instrucoes, resultado_final

    for expressao in expressoes:
        instrucoes, resultado = avaliar_expressao(expressao)
        instrucoes_totais.append(instrucoes)
        if resultado is not None:
            historico.append(resultado)

    imprimir_execucao(expressoes, instrucoes_totais, historico, memoria)
    os.makedirs("resultados_expressoes", exist_ok=True)
    salvar_executar_arq(instrucoes_totais, f'resultados_expressoes/{nome_arq}')
    
    return historico, memoria   # retorno para o main usar
            
def exibirResultados(resultados: list):
    ''' Exibe os resultados das expressões em formatação clara.
        - Números reais são exibidos sem casas decimais.
        - Números reais são exibidos com uma casa decimal.
    '''
    print("\n" + "="*60)
    print("RESULTADOS DAS EXPRESSÕES")
    print("="*60)

    if not resultados:
        print("     Nenhum resultado calculado.")
    else:
        for i, val in enumerate(resultados, 1):
            if val == int(val):
                print(f"     Expressão {i:2d} : {int(val)}")
            else:
                print(f"     Expressão {i:2d} : {val:.1f}")
    print("="*60)


def imprimir_execucao(expressoes, instrucoes, historico=None, memoria=None):

    print("\n" + "="*60)
    print("EXECUÇÃO DAS EXPRESSÕES")
    print("="*60)

    for i in range(len(expressoes)):

        print(f"\nExpressão {i+1}:")

        # Mostrar tokens da expressão
        tokens_str = []

        for token in expressoes[i]:
            if token['tipo'] != TOKEN_LPAREN and token['tipo'] != TOKEN_RPAREN:
                tokens_str.append(token['valor'])

        print("Tokens:", " ".join(tokens_str))

        print("Instruções geradas:")

        for instr in instrucoes[i]:
            print("   ", instr)

    print("\n" + "="*60)

def executar_testes_expressao():

    print("="*60)
    print("TESTES DO executarExpressao")
    print("="*60)

    arquivos = [ "teste1.txt", "teste2.txt", "teste3.txt" ]

    for nome_arquivo in arquivos:

        print(f"\nTestando arquivo: {nome_arquivo}")
        print("-"*50)

        try:
            with open(nome_arquivo, 'r', encoding='utf-8') as f:
                linhas = f.readlines()
        except FileNotFoundError:
            print(f"Arquivo {nome_arquivo} não encontrado.")
            continue

        expressoes = []

        for linha in linhas:
            linha = linha.strip()

            if not linha or linha.startswith('#'):
                continue

            tokens_linha = []

            valido = parseExpressao(linha, tokens_linha)

            if valido:
                expressoes.append([
                    t.to_dict() for t in tokens_linha
                ])
        base = nome_arquivo.replace(".txt", "")
        executarExpressao(expressoes, f"{base}_instrucoes.json")
        print("Teste concluído.")

def salvar_executar_arq(instrucoes, nome_arq="instrucoes.json"):
    try:
        with open(nome_arq, "w", encoding="utf-8") as f:
            json.dump(instrucoes, f, indent=4)
        print("Arquivo de executarExpressao gerado")
    except Exception:
        print("Erro na geração de arquivo")

def executar_testes_assembly():
    print("="*60)
    print("TESTES DE GERAÇÃO DE ASSEMBLY")
    print("="*60)

    arquivos = ["teste1", "teste2", "teste3"]
    os.makedirs("resultados_assembly", exist_ok=True)

    for base in arquivos:
        nome_json = f"resultados_expressoes/{base}_instrucoes.json"
        print(f"\nGerando assembly para: {nome_json}")
        print("-"*50)

        if not os.path.exists(nome_json):
            print(f"Arquivo não encontrado!")
            print(f"Rodar: py analisador_lexico.py --testes-exec")
        try:
            tokens = lerArquivo(nome_json)
            execucao, dados = gerarAssembly(tokens)
            nome_saida = f"resultados_assembly/{base}_assembly.s"
            criarArquivoAssembly(execucao, dados, nome_saida)
            print(f"Assembly gerado: {nome_saida}")

        except Exception as e:
            print(f"Erro ao gerar assembly para {nome_json}: {e}")


# ===== MAIN =====
def main():
    print("main")
    if len(sys.argv) < 2:
        print("Uso: python analisador_lexico.py <arquivo.txt>")
        print("     python analisador_lexico.py --testes")
        print("     python analisar_lexico.py --testes-exec")
        print("     python analisar_lexico.py --testes-assembly")
        print("     python analisar_lexico.py --testes-aluno4")
        sys.exit(1)

    if sys.argv[1] == "--testes":
        sucesso = executar_testes_aluno1()
        sys.exit(0 if sucesso else 1)
    elif sys.argv[1] == "--testes-exec":
        executar_testes_expressao()
        sys.exit(0)
    elif sys.argv[1] == "--testes-assembly":
        executar_testes_assembly()
        sys.exit(0)
    elif sys.argv[1] == "--testes-aluno4":
        sucesso = executar_testes_aluno4()
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
            continue    # pula linhas vazias e comentários

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

    #executarExpressao(expressoes, base + "_instrucoes.json")
    historico, memoria = executarExpressao(expressoes, base + "_instrucoes.json")

    # exibirResultados com os valores calculados
    exibirResultados(historico)

    print("=" * 60)
    if tem_erros:
        print("AVISO: foram encontrados erros léxicos.")
    else:
        print("Análise concluída sem erros.")

    sys.exit(1 if tem_erros else 0)

if __name__ == "__main__":
    main()