"""
Utilitários para gerenciamento de fibras ópticas.
Implementa padrão de cores ABNT NBR 14565 / TIA-598.
"""

# Padrão ABNT NBR 14565 / TIA-598
# Sequência de cores de 1 a 12 (repete ciclicamente para índices maiores)
FIBER_COLORS = {
    1: {'name': 'Verde', 'hex': '#009900'},
    2: {'name': 'Amarelo', 'hex': '#FFFF00'},
    3: {'name': 'Branco', 'hex': '#FFFFFF'},
    4: {'name': 'Azul', 'hex': '#0000FF'},
    5: {'name': 'Vermelho', 'hex': '#FF0000'},
    6: {'name': 'Violeta', 'hex': '#800080'},
    7: {'name': 'Marrom', 'hex': '#A52A2A'},
    8: {'name': 'Rosa', 'hex': '#FFC0CB'},
    9: {'name': 'Preto', 'hex': '#000000'},
    10: {'name': 'Cinza', 'hex': '#808080'},
    11: {'name': 'Laranja', 'hex': '#FFA500'},
    12: {'name': 'Aqua', 'hex': '#00FFFF'},
}


def get_color_for_index(index):
    """
    Retorna a cor baseada no índice (1-based).
    Se for maior que 12, repete o ciclo (ex: 13 é Verde novamente).
    
    Args:
        index: Posição da fibra/tubo (1-based)
    
    Returns:
        dict: {'name': str, 'hex': str}
    
    Examples:
        >>> get_color_for_index(1)
        {'name': 'Verde', 'hex': '#009900'}
        >>> get_color_for_index(13)
        {'name': 'Verde', 'hex': '#009900'}
    """
    # Normaliza para 1-12 (cíclico)
    normalized_index = ((index - 1) % 12) + 1
    return FIBER_COLORS.get(normalized_index, FIBER_COLORS[1])


def get_all_colors():
    """
    Retorna todas as cores disponíveis no padrão.
    
    Returns:
        list: Lista de dicionários com dados das cores
    """
    return [FIBER_COLORS[i] for i in range(1, 13)]
