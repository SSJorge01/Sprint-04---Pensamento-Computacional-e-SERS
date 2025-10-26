# ai.py
# -------------------------------------------------------------------
# Módulo de análise de dados e geração de insights para o sistema GoodWe
# -------------------------------------------------------------------
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def analisar_com_deterministico(resumo: dict, tipo="dia"):
    """
    Gera análise determinística baseada nos cálculos de dia ou semana,
    sem usar LLM.
    """
    if tipo == "dia":
        energia = resumo.get("energia_dia", 0)
        pico = resumo.get("pico_potencia", 0)
        soc_ini = resumo.get("soc_ini", 0)
        soc_fim = resumo.get("soc_fim", 0)

        analise = f"""
        ### Relatório Diário

        - Energia do dia: {energia:.2f} kWh
        - Pico de potência: {pico:.2f} kW
        - Nível da Bateria: Começou o dia com {soc_ini}% e terminou com {soc_fim}%.

        **Interpretação:**
        - **Geração:** Sua geração de {energia:.2f} kWh foi {'excelente. É energia suficiente para alimentar os principais eletrodomésticos da casa por várias horas!' if energia > 20 else 'moderada. Em dias assim, vale a pena focar o consumo nos horários de pico solar.'}
        - **Pico de Potência:** Seu sistema atingiu um pico de {pico:.2f} kW. Isso mostra que ele está {'operando com força total sob o sol.' if pico > 3 else 'operando com uma potência mais contida, talvez devido à nebulosidade.'}
        - **Uso da Bateria:** A variação no nível da bateria indica que você {'aproveitou bem a energia armazenada para uso noturno ou em momentos sem sol.' if soc_fim - soc_ini > 15 else 'dependeu pouco da bateria hoje, provavelmente porque a geração solar supriu bem o consumo.'}

        **Recomendações:**
        - Use aparelhos de alto consumo durante as horas de maior geração solar.
        - Programe recarga de veículos elétricos entre 10h e 14h.
        """
    else:
        autossuf = resumo["autossuficiencia"]
        melhor = resumo["melhor_dia"]
        pior = resumo["pior_dia"]

        analise = f"""
        ### Relatório Semanal

        - Total gerado: {resumo['total_geracao']:.2f} kWh
        - Total consumido: {resumo['total_consumo']:.2f} kWh
        - Autossuficiência: {autossuf:.1f}%
        - Melhor dia: {melhor['data'].strftime('%d/%m/%Y')} ({melhor['geracao']:.1f} kWh)
        - Pior dia: {pior['data'].strftime('%d/%m/%Y')} ({pior['geracao']:.1f} kWh)

        **Interpretação:**
        - **Autossuficiência:** Com {autossuf:.1f}%, seu sistema gerou mais energia do que o necessário, {'o que é ótimo e reduz significativamente sua dependência da rede elétrica.' if autossuf > 100 else 'cobriu a maior parte do seu consumo, um excelente resultado.' if autossuf > 70 else 'e você precisou complementar com a energia da rede. Podemos otimizar isso!'}
        - **Variação na Geração:** É normal haver variação durante a semana devido às condições do tempo. Sua geração variou entre {pior['geracao']:.1f} kWh (no dia {pior['data'].strftime('%d/%m')}) e um pico de {melhor['geracao']:.1f} kWh (no dia {melhor['data'].strftime('%d/%m')}).

        **Recomendações:**
        - **Otimização:** {'Você já gera um bom excedente de energia. Para maximizar a economia, tente concentrar o uso de equipamentos pesados (como ar condicionado ou máquina de lavar) nos horários de sol.' if resumo['horas_excedente_media'] > 4 else 'Para aumentar sua autossuficiência, especialmente à noite, a instalação de baterias seria um excelente próximo passo.'}        - Faça manutenção preventiva se a geração cair abaixo da média.
        """
    return analise


def analisar_expansao_deterministico(consumo_total_kwh, producao_semanal_kwh, periodo="7d"):
    """
    Análise determinística da necessidade de expansão (sem LLM).
    """
    dias = 7 if periodo == "7d" else 30
    consumo_medio_dia = consumo_total_kwh / dias
    producao_media_dia = producao_semanal_kwh / 7
    capacidade_estimada_kw = producao_media_dia / 4
    limite_operacional = capacidade_estimada_kw * 0.8 * dias * 4

    necessidade = "⚠️ Expansão necessária" if consumo_total_kwh > limite_operacional else "✅ Expansão não necessária"

    inversores_goodwe = [3, 5, 10, 15, 20]
    capacidade_necessaria_kw = consumo_medio_dia / 4
    inversor_sugerido = next((inv for inv in inversores_goodwe if inv >= capacidade_necessaria_kw), ">20")

    return f"""
    ### Análise de Expansão

    - Consumo total analisado: {consumo_total_kwh:.2f} kWh ({periodo})
    - Produção semanal estimada: {producao_semanal_kwh:.2f} kWh
    - Potência estimada do seu sistema: {capacidade_estimada_kw:.2f} kW
    - Limite de geração segura (80% da capacidade): {limite_operacional:.2f} kWh no período de {periodo}.
    - **Diagnóstico:** { 'Com base no seu consumo atual, seu sistema está operando confortavelmente dentro da capacidade de geração.' if consumo_total_kwh <= limite_operacional else 'Seu consumo está próximo ou excede o limite de geração segura do seu sistema atual.'}
    - **Próximo Passo Sugerido:** { 'Nenhuma ação é necessária no momento.' if consumo_total_kwh <= limite_operacional else f'Para suportar sua demanda de energia com mais folga, um inversor GoodWe de pelo menos {inversor_sugerido} kW seria o mais indicado.'}
    """
