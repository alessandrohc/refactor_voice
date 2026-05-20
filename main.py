import json
import random
import speech_recognition as sr
import google.generativeai as genai
from dotenv import load_dotenv
import os
import threading
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

# Inicializa o console do rich para formatação bonita no terminal
console = Console()

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configurar API Key do Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Variável global para controlar a gravação
recording_active = False

def carregar_pergunta_aleatoria(arquivo="perguntas.json"):
    """Carrega o JSON de perguntas e sorteia uma categoria e uma pergunta aleatória."""
    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            perguntas_db = json.load(f)
            
        categoria = random.choice(list(perguntas_db.keys()))
        pergunta = random.choice(perguntas_db[categoria])
        
        print(f"\n[{categoria}]")
        print(f"Pergunta: {pergunta}\n")
        
        return pergunta
    except FileNotFoundError:
        print(f"Erro: O arquivo '{arquivo}' não foi encontrado no diretório atual.")
        return None
    except json.JSONDecodeError:
        print(f"Erro: O arquivo '{arquivo}' não é um JSON válido.")
        return None

def aguardar_tecla_parada():
    global recording_active
    input()
    recording_active = False

def gravar_audio_e_transcrever():
    """Captura áudio do microfone até o usuário apertar ENTER para parar."""
    global recording_active
    recognizer = sr.Recognizer()
    
    input("Pressione ENTER para começar a falar...")
    
    with sr.Microphone() as source:
        print("\nAjustando para o ruído ambiente... aguarde 1 segundo.")
        recognizer.adjust_for_ambient_noise(source)
        
        print("🎙️ Ouvindo... (Pressione ENTER novamente quando terminar de falar)")
        
        recording_active = True
        
        # Inicia thread para monitorar o ENTER e parar a gravação
        stop_thread = threading.Thread(target=aguardar_tecla_parada)
        stop_thread.start()
        
        frames = []
        try:
            # Gravando em blocos curtos enquanto a thread não diz para parar
            while recording_active:
                # Pegar pequenos pedaços de áudio
                try:
                    # phrase_time_limit curto para não bloquear muito tempo caso aperte ENTER
                    audio_chunk = recognizer.listen(source, timeout=1, phrase_time_limit=1)
                    frames.append(audio_chunk.get_raw_data())
                except sr.WaitTimeoutError:
                    continue # Continua ouvindo se não teve som no pedaço
                    
            print("Processando áudio...")
            
            if not frames:
                print("Nenhum áudio detectado.")
                return None
                
            # Junta os frames coletados em um único AudioData
            audio_data = sr.AudioData(b''.join(frames), source.SAMPLE_RATE, source.SAMPLE_WIDTH)
            
            # Reconhecimento de fala
            transcricao = recognizer.recognize_google(audio_data, language='en-US')
            print(f"\n📝 Sua transcrição: \"{transcricao}\"")
            return transcricao
            
        except sr.UnknownValueError:
            print("Erro: Não foi possível entender o áudio.")
            return None
        except sr.RequestError as e:
            print(f"Erro na requisição ao serviço de reconhecimento de fala: {e}")
            return None
        except Exception as e:
            print(f"Ocorreu um erro inesperado na gravação: {e}")
            return None

def avaliar_resposta_com_gemini(pergunta, transcricao):
    """Envia a pergunta e a transcrição para a API do Gemini e imprime o feedback."""
    print("\n🤖 Analisando sua resposta com o Gemini...\n")
    
    prompt = f"""
You are an English Fluency Coach specialized in helping experienced software engineers recover spoken fluency after years without practice.

The user already understands English well, but currently struggles with:
- mentally translating from Portuguese to English
- hesitation during speech
- forgetting words while speaking
- overthinking grammar
- losing fluency and speaking rhythm

IMPORTANT:
The goal is NOT perfect grammar.
The goal is:
- fluent communication
- continuous speaking
- faster thinking in English
- confidence during interviews
- recovering automatic speech

You are currently operating in RECOVERY MODE (Mode 1).

RECOVERY MODE RULES:
- Be supportive and encouraging.
- Prioritize communication over correctness.
- Do NOT over-correct small grammar mistakes.
- Avoid sounding like a strict English teacher.
- Help the user simplify communication.
- Encourage natural spoken English.
- Focus on reducing mental translation and hesitation.
- Prefer short and practical feedback.

Analyze the user's transcribed answer using the structure below:

# 1. Fluency & Communication
- Did the answer flow naturally?
- Were there signs of hesitation or overcomplicated phrasing?
- Did the user communicate ideas clearly despite mistakes?

# 2. Mental Translation Detection
Identify phrases that sound like literal translations from Portuguese or unnatural constructions.
Explain WHY they sound unnatural in spoken English.

# 3. Simpler & More Natural Alternatives
Suggest simpler spoken alternatives that are easier to say naturally during interviews.
Focus on:
- easier sentence structures
- natural spoken English
- interview-friendly communication
- reducing cognitive load

# 4. Vocabulary Recovery
Suggest useful "speech chunks" and interview expressions the user can reuse naturally.
Examples:
- "One challenge we faced was..."
- "I worked closely with..."
- "We had to balance..."
- "The main issue was..."

# 5. Improved Spoken Version
Provide a more natural spoken version of the answer.
IMPORTANT:
- Keep it conversational
- Keep it easy to speak
- Avoid overly sophisticated vocabulary
- Optimize for fluency and confidence
- Do not make it sound robotic or excessively formal

# 6. Coach Feedback
Give short motivational feedback focused on speaking performance.
Examples:
- "Your ideas are clear. Now we need to reduce hesitation."
- "Try using shorter sentences when you feel stuck."
- "Good communication overall — focus less on perfection."

Question asked:
{pergunta}

User transcribed answer:
{transcricao}

Respond in Markdown.

IMPORTANT:
- Explanations must be in Portuguese.
- All English examples must remain in English.
- Maintain a supportive speaking-coach tone, not a strict grammar-teacher tone.
"""

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        # Renderiza o markdown de forma limpa e visual no terminal
        markdown_view = Markdown(response.text)
        painel = Panel(markdown_view, title="✨ Avaliação do Gemini ✨", border_style="cyan", expand=False)
        
        print("\n")
        console.print(painel)
        print("\n")
    except Exception as e:
        print(f"Erro ao chamar a API do Gemini: {e}")

def main():
    print("="*60)
    print("🎙️   Treinador de Inglês para Entrevistas Tech   🎙️")
    print("="*60)
    
    # Verifica se a API key está configurada
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key == "sua_chave_aqui":
        print("⚠️ Aviso: GOOGLE_API_KEY não configurada ou usando o valor padrão no arquivo .env.")
        print("Por favor, edite o arquivo .env e adicione sua chave de API real do Google Gemini antes de continuar.")
        return
        
    pergunta = carregar_pergunta_aleatoria()
    if not pergunta:
        return
        
    transcricao = gravar_audio_e_transcrever()
    if transcricao:
        avaliar_resposta_com_gemini(pergunta, transcricao)
    else:
        print("\nNão foi possível obter a transcrição para análise.")

if __name__ == "__main__":
    main()
