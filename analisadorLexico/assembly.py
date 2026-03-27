import json

def int_float(valor):
    try:
        int(valor)
        return "int"
    except ValueError:
        return "float"
    
def tipo_valor(valor, dados_expressoes):
    nome = obter_nome_var(valor, dados_expressoes)
    if nome.startswith("s"):
        return "float"
    if nome.startswith("r"):
        return "int"
    try:
        if "." in valor:
            float(valor)
            return "float"
        else:
            int(valor)
            return "int"
    except:
        return "float"

def tipo_operacao(v1, v2, dados_expressoes):
    if tipo_valor(v1, dados_expressoes) == "float":
        return "float"
    if tipo_valor(v2, dados_expressoes) == "float":
        return "float"
    return "int"

def obter_nome_var(valor, dados_expressoes):
    if valor in dados_expressoes:
        return dados_expressoes[valor]
    return valor

def se_registrador(valor):
    return valor.startswith("s") or valor.startswith("r")

def comentario_expressao(expressao):
    texto = "@ ("
    for token in expressao:
        if len(token) > 1:
            texto += token[1] + " "
        else:
            texto+= token[0] + " "
    texto = texto.strip() + ")"
    return texto

def gerarAssembly(tokens):
    dados_expressoes = {}
    bloco_data = []
    bloco_executar = []

    cont = 1
    registrador = 0
    cont_div = 0

    # Bloco .data
    for expressao in tokens:
        for token in expressao:
            if len(token) > 1:
                valor = token[1]
                if valor not in dados_expressoes:
                    # valor (var) para cada número
                    try:
                        float(valor)
                        var = f"valor{cont}"
                        dados_expressoes[valor] = var
                        cont += 1
                    # se não for número - var SOMA
                    except:
                        dados_expressoes[valor] = valor
    
    pilha = []
    for expressao in tokens:
        bloco_executar.append(comentario_expressao(expressao))

        for token in expressao:
            instrucao = token[0]

            if instrucao == "PUSH":
                valor = token[1]
                pilha.append(valor)
                
            elif instrucao == "STORE":
                valor = pilha.pop()
                destino = token[1]
                nome_var = obter_nome_var(valor, dados_expressoes)
                tipo_destino = tipo_valor(valor, dados_expressoes)

                # criar variável se não existir
                if destino not in dados_expressoes:
                    dados_expressoes[destino] = destino
                    if tipo_destino == "float":
                        bloco_data.append(f"{destino}: .float 0.0")
                    else:
                        bloco_data.append(f"{destino}: .word 0")

                if tipo_destino == "float":
                    if se_registrador(nome_var):
                        bloco_executar.append(f"LDR r0, ={destino}")
                        bloco_executar.append(f"VSTR {nome_var}, [r0]")
                    # Se numeral
                    else:
                        bloco_executar.append(f"LDR r0, ={nome_var}")
                        bloco_executar.append(f"VLDR s{registrador}, [r0]")

                        bloco_executar.append(f"LDR r1, ={destino}")
                        bloco_executar.append(f"VSTR s{registrador}, [r1]")
                        registrador+=1
                else:
                    if se_registrador(nome_var):
                        bloco_executar.append(f"MOV r2, {nome_var}")
                    else:
                        bloco_executar.append(f"LDR r0, ={nome_var}")
                        bloco_executar.append("LDR r2, [r0]")
                    bloco_executar.append(f"LDR r1, ={destino}")
                    bloco_executar.append("STR r2, [r1]")
            
            elif instrucao == "LOAD":
                origem = token[1]
                nome_var = obter_nome_var(origem, dados_expressoes)
                tipo = tipo_valor(origem, dados_expressoes)

                if tipo == "float":
                    bloco_executar.append(f"LDR r0, ={nome_var}")
                    bloco_executar.append(f"VLDR s{registrador}, [r0]")
                    pilha.append(f"s{registrador}")
                    registrador += 1
                else:
                    bloco_executar.append(f"LDR r0, ={nome_var}")
                    bloco_executar.append("LDR r2, [r0]")
                    pilha.append("r2")
                    
            elif instrucao == "RES":
                if not pilha:
                    raise Exception("Erro: pilha vazia no RES")
                valor = pilha.pop()
                destino = token[1]

                try:
                    float(destino)
                    valor_original = destino
                    destino = f"res{valor_original.replace('.', '_')}"
                    # Impedir res obter valor'id'
                    if valor_original in dados_expressoes:
                        del dados_expressoes[valor_original]
                except:
                    pass

                nome_var = obter_nome_var(valor, dados_expressoes)
                tipo_destino = tipo_valor(valor, dados_expressoes)

                if destino not in dados_expressoes:
                    dados_expressoes[destino] = destino

                    if tipo_destino == "float":
                        bloco_data.append(f"{destino}: .float 0.0")
                    else:
                        bloco_data.append(f"{destino}: .word 0")

                if tipo_destino == "float":
                    if se_registrador(nome_var):
                        bloco_executar.append(f"LDR r0, ={destino}")
                        bloco_executar.append(f"VSTR {nome_var}, [r0]")
                    else:
                        bloco_executar.append(f"LDR r0, ={nome_var}")
                        bloco_executar.append(f"VLDR s{registrador}, [r0]")
                        bloco_executar.append(f"LDR r1, ={destino}")
                        bloco_executar.append(f"VSTR s{registrador}, [r1]")
                # INT
                else:
                    if se_registrador(nome_var):
                        bloco_executar.append(f"MOV r2, {nome_var}")
                    else:
                        bloco_executar.append(f"LDR r0, ={nome_var}")
                        bloco_executar.append("LDR r2, [r0]")
                    bloco_executar.append(f"LDR r1, ={destino}")
                    bloco_executar.append("STR r2, [r1]")

            # Operacions
            elif instrucao in ["ADD", "SUB", "MUL", "DIV", "IDIV", "MOD", "POW"]:
                op2 = pilha.pop()
                op1 = pilha.pop()

                tipo = tipo_operacao(op1, op2, dados_expressoes)

                nome_var1 = obter_nome_var(op1, dados_expressoes)
                nome_var2 = obter_nome_var(op2, dados_expressoes)

                # Divisão em float e int - usei instruções vector - pensando em float
                if tipo == "float":
                    s0 = f"s{registrador}"
                    registrador += 1
                    s1 = f"s{registrador}"
                    registrador += 1
                    s2 = f"s{registrador}"
                    registrador += 1

                    if se_registrador(nome_var1):
                        bloco_executar.append(f"VMOV {s0}, {nome_var1}")
                    else:
                        bloco_executar.append(f"LDR r0, ={nome_var1}")
                        bloco_executar.append(f"VLDR {s0}, [r0]")

                    if se_registrador(nome_var2):
                        bloco_executar.append(f"VMOV {s1}, {nome_var2}")
                    else:
                        bloco_executar.append(f"LDR r1, ={nome_var2}")
                        bloco_executar.append(f"VLDR {s1}, [r1]")

                    if instrucao == "ADD":
                        bloco_executar.append(
                            f"VADD.F32 {s2}, {s0}, {s1}"
                        )

                    elif instrucao == "SUB":
                        bloco_executar.append(
                            f"VSUB.F32 {s2}, {s0}, {s1}"
                        )

                    elif instrucao == "MUL":
                        bloco_executar.append(
                            f"VMUL.F32 {s2}, {s0}, {s1}"
                        )

                    elif instrucao in ["DIV", "IDIV"]:
                        bloco_executar.append(
                            f"VDIV.F32 {s2}, {s0}, {s1}"
                        )
                    pilha.append(s2)

                else:
                    if se_registrador(nome_var1):
                        bloco_executar.append(f"MOV r2, {nome_var1}")
                    elif nome_var1.isdigit():
                        bloco_executar.append(f"MOV r2, #{nome_var1}")
                    else:
                        bloco_executar.append(f"LDR r0, ={nome_var1}")
                        bloco_executar.append("LDR r2, [r0]")

                    if se_registrador(nome_var2):
                        bloco_executar.append(f"MOV r3, {nome_var2}")
                    elif nome_var2.isdigit():
                        bloco_executar.append(f"MOV r3, #{nome_var2}")
                    else:
                        bloco_executar.append(f"LDR r1, ={nome_var2}")
                        bloco_executar.append("LDR r3, [r1]")

                    if instrucao == "ADD":
                        bloco_executar.append("ADD r4, r2, r3")

                    elif instrucao == "SUB":
                        bloco_executar.append("SUB r4, r2, r3")

                    elif instrucao == "MUL":
                        bloco_executar.append("MUL r4, r2, r3")

                    elif instrucao in ["DIV", "IDIV"]:
                        cont_div += 1
                        loop = f"div_loop{cont_div}"
                        end = f"div_end{cont_div}"

                        bloco_executar.append("MOV r4, #0")
                        bloco_executar.append(f"{loop}:")
                        bloco_executar.append("CMP r2, r3")
                        bloco_executar.append(f"BLT {end}")
                        bloco_executar.append("SUB r2, r2, r3")
                        bloco_executar.append("ADD r4, r4, #1")
                        bloco_executar.append(f"B {loop}")
                        bloco_executar.append(f"{end}:")

                    elif instrucao == "MOD":
                        cont_div += 1
                        loop = f"mod_loop{cont_div}"
                        end = f"mod_end{cont_div}"

                        bloco_executar.append(f"{loop}:")
                        bloco_executar.append("CMP r2, r3")
                        bloco_executar.append(f"BLT {end}")
                        bloco_executar.append("SUB r2, r2, r3")
                        bloco_executar.append(f"B {loop}")
                        bloco_executar.append(f"{end}:")
                        bloco_executar.append("MOV r4, r2")

                    elif instrucao == "POW":
                        cont_div += 1
                        loop = f"pow_loop{cont_div}"
                        end = f"pow_end{cont_div}"

                        bloco_executar.append("MOV r4, #1")
                        bloco_executar.append(f"{loop}:")
                        bloco_executar.append("CMP r3, #0")
                        bloco_executar.append(f"BEQ {end}")
                        bloco_executar.append("MUL r4, r4, r2")
                        bloco_executar.append("SUB r3, r3, #1")
                        bloco_executar.append(f"B {loop}")
                        bloco_executar.append(f"{end}:")
                    pilha.append("r4")
        bloco_executar.append("")

    # Estrutura .data
    for val, ident in dados_expressoes.items():
        if ident.startswith("res"):
            continue
        try:
            float(val)
            if int_float(val) == "float":
                bloco_data.append(f"{ident}: .float {val}")
            else:
                bloco_data.append(f"{ident}: .word {val}")
        except:
            # é variável (ex: SOMA)
            ja_existe = any(linha.startswith(f"{ident}:") for linha in bloco_data)
            if not ja_existe:
                bloco_data.append(f"{ident}: .float 0.0")

    return bloco_executar, bloco_data

def criarArquivoAssembly(execucao_instrucoes, definicao_dados, nome="arquivo_assembly.s"):
    try:
        with open(nome, "w") as arq:

            arq.write(
                ".global _start\n"
                "_start:\n"
            )

            for linha in execucao_instrucoes:
                arq.write("\t" + linha + "\n")

            arq.write(
                "\tend:\n"
                "\tB end\n"
            )

            arq.write("\n.data\n")

            for linha in definicao_dados:
                arq.write("\t" + linha + "\n")
        print("Arquivo Assembly gerado com sucesso.")
    except IOError as e:
        print(f"Erro de escrita no arquivo: {e}")
    except Exception as e:
        print(f"Erro ao gerar o arquivo: {e}")

def lerArquivo(nomeArquivo):
    try:
        with open(nomeArquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Erro: arquivo '{nomeArquivo}' não encontrado.")
        exit(1)
    except Exception as e:
        print(f"Erro ao abrir o arquivo '{nomeArquivo}': {e}")
        exit(1)