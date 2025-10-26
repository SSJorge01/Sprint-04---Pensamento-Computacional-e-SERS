# -*- coding: utf-8 -*-
import logging

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
import ask_sdk_core.utils as ask_utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ===== Dataset fixo: produção e consumo por hora =====
DADOS_DIA = [
    {"hora": h,
     "producao": (0 if h < 6 or h > 18 else max(0, -0.1*(h-13)**2 + 7)),  # curva parabólica do sol
     "consumo": (1.5 if 0 <= h < 6 else 2 if 6 <= h < 18 else 3.5)}        # mais consumo à noite
    for h in range(24)
]

def calcular_totais():
    producao_total = round(sum(item["producao"] for item in DADOS_DIA), 2)
    consumo_total = round(sum(item["consumo"] for item in DADOS_DIA), 2)
    saldo = round(producao_total - consumo_total, 2)
    return producao_total, consumo_total, saldo

def melhor_horario():
    diffs = [(item["hora"], item["producao"] - item["consumo"]) for item in DADOS_DIA]
    melhor = max(diffs, key=lambda x: x[1])
    return melhor[0]

# ===== Handlers Alexa =====
class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        speak_output = ("Olá! Eu sou sua assistente de energia solar. ")
        return handler_input.response_builder.speak(speak_output).ask("Quer saber consumo, produção, saldo ou melhor horário?").response


class ConsumoIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("ConsumoIntent")(handler_input)

    def handle(self, handler_input):
        producao, consumo, saldo = calcular_totais()

        speak_output = f"Hoje você gastou aproximadamente {consumo} quilowatts hora. "

        # Condicional: consumo na faixa de ~50 kWh → comparação com ar condicionado
        if 45 <= consumo <= 55:
            speak_output += "Isso é parecido com manter um ar condicionado ligado por cerca de 8 horas. "

        # Condicional: consumo muito alto
        if consumo > 60:
            speak_output += "Esse consumo está acima do normal, pode ser um bom momento para revisar seus hábitos. "

        return handler_input.response_builder.speak(speak_output).ask("Quer que eu compare com a produção de energia?").response


class ProducaoIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("ProducaoIntent")(handler_input)

    def handle(self, handler_input):
        producao, consumo, saldo = calcular_totais()

        speak_output = f"Sua produção solar hoje rendeu aproximadamente {producao} quilowatts hora. "

        # Condicional: produção muito alta
        if producao > 70:
            speak_output += "Parabéns, foi um dia excelente de geração solar, quase como um dia de verão ensolarado! "

        # Condicional: produção baixa
        if producao < 30:
            speak_output += "A produção ficou abaixo da média, provavelmente devido ao clima de hoje. "

        return handler_input.response_builder.speak(speak_output).ask("Deseja que eu diga se produziu mais ou menos que consumiu?").response


class SaldoIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("SaldoIntent")(handler_input)

    def handle(self, handler_input):
        producao, consumo, saldo = calcular_totais()

        if saldo >= 0:
            speak_output = (
                f"Boa notícia! Você produziu {producao} quilowatts hora e consumiu {consumo}. "
                f"Sobraram {saldo} quilowatts hora de energia hoje. "
            )

            # Condicional: sobra muito grande
            if saldo > 20:
                speak_output += "Esse excedente seria ótimo para carregar um carro elétrico ou armazenar em baterias. "

        else:
            speak_output = (
                f"Atenção: você produziu {producao} quilowatts hora e consumiu {consumo}. "
                f"Faltaram {abs(saldo)} quilowatts hora para equilibrar o dia. "
            )

            # Condicional: déficit alto
            if abs(saldo) > 15:
                speak_output += "Esse déficit foi significativo, considere economizar nos horários de pico amanhã. "

        return handler_input.response_builder.speak(speak_output).ask("Posso sugerir o melhor horário de uso?").response


class MelhorHorarioIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("MelhorHorarioIntent")(handler_input)

    def handle(self, handler_input):
        hora = melhor_horario()
        producao, consumo, saldo = calcular_totais()

        speak_output = f"O pico de geração solar hoje foi por volta das {hora} horas. "

        # Condicional: saldo positivo
        if saldo > 0:
            speak_output += "Esse é o momento perfeito para ligar aparelhos como máquina de lavar ou carregar seu carro. "

        # Condicional: saldo negativo
        if saldo < 0:
            speak_output += "Mesmo com esse pico, sua produção não superou o consumo total do dia. Talvez valha economizar amanhã. "

        return handler_input.response_builder.speak(speak_output).ask("Deseja ouvir o saldo final de energia?").response


class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        speak_output = "Você pode me perguntar pelo consumo, produção, saldo ou melhor horário para usar energia. O que deseja?"
        return handler_input.response_builder.speak(speak_output).ask(speak_output).response


class CancelOrStopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        return handler_input.response_builder.speak("Até logo! Continue aproveitando bem sua energia solar.").response


class FallbackIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.speak(
            "Desculpe, não entendi. Você pode perguntar pelo consumo, produção, saldo ou melhor horário."
        ).ask("Quer que eu fale do consumo, produção, saldo ou melhor horário?").response


class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        logger.error(exception, exc_info=True)
        speak_output = "Desculpe, houve um erro. Pode repetir sua pergunta?"
        return handler_input.response_builder.speak(speak_output).ask("Você pode tentar de novo?").response


# ===== Skill Builder =====
sb = SkillBuilder()
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(ConsumoIntentHandler())
sb.add_request_handler(ProducaoIntentHandler())
sb.add_request_handler(SaldoIntentHandler())
sb.add_request_handler(MelhorHorarioIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()
