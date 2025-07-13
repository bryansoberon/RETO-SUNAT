#!/usr/bin/env python
"""
Generador de RUCs válidos según algoritmo oficial SUNAT
"""

def generar_ruc_valido():
    """Genera un RUC válido para pruebas"""
    import random
    
    # Generar 10 dígitos aleatorios
    primeros_10 = ''.join([str(random.randint(0, 9)) for _ in range(10)])
    
    # Calcular el dígito verificador
    pesos = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    suma = 0
    for i in range(10):
        suma += int(primeros_10[i]) * pesos[i]
    
    resto = suma % 11
    digito_calculado = 11 - resto
    
    if digito_calculado == 11:
        digito_calculado = 0
    elif digito_calculado == 10:
        digito_calculado = 1
    
    return primeros_10 + str(digito_calculado)

def validar_ruc_sunat(ruc):
    """Valida el RUC usando el algoritmo oficial de SUNAT"""
    if not ruc or len(ruc) != 11 or not ruc.isdigit():
        return False
    
    pesos = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    primeros_10 = ruc[:10]
    digito_verificador = int(ruc[10])
    
    suma = 0
    for i in range(10):
        suma += int(primeros_10[i]) * pesos[i]
    
    resto = suma % 11
    digito_calculado = 11 - resto
    
    if digito_calculado == 11:
        digito_calculado = 0
    elif digito_calculado == 10:
        digito_calculado = 1
    
    return digito_calculado == digito_verificador

if __name__ == "__main__":
    print("🔧 Generando RUCs válidos para pruebas...")
    print("=" * 50)
    
    rucs_validos = []
    for i in range(5):
        ruc = generar_ruc_valido()
        rucs_validos.append(ruc)
        print(f"RUC {i+1}: {ruc} - {'✅ VÁLIDO' if validar_ruc_sunat(ruc) else '❌ INVÁLIDO'}")
    
    print("\n💡 RUCs válidos para usar en pruebas:")
    for i, ruc in enumerate(rucs_validos):
        print(f"   ruc_{i+1} = '{ruc}'")
    
    print(f"\n🎯 RUC emisor recomendado: {rucs_validos[0]}")
    print(f"🎯 RUC cliente recomendado: {rucs_validos[1]}") 