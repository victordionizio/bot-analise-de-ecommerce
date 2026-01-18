import time
import threading
from flask import Flask, render_template, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import pymysql.cursors
import os
import uuid # Para gerar IDs de sessão únicos

session_counter = 0 # Inicializado globalmente, será atualizado por init_db()

def get_db_connection():
    # Configurações do banco de dados (Exemplo)
    conn = pymysql.connect(host='localhost',
                           user='seu_usuario',
                           password='sua_senha',
                           database='seu_banco',
                           cursorclass=pymysql.cursors.DictCursor) # Retorna linhas como dicionários
    return conn

def init_db():
    global session_counter
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs_testeSite (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL, # Ajustado para suportar TestandoSite_X
                timestamp DATETIME NOT NULL,
                step VARCHAR(255) NOT NULL,
                status VARCHAR(255) NOT NULL,
                response_time REAL,
                message TEXT,
                error_message TEXT
            )
        ''')
        conn.commit()

        # Tenta recuperar o último session_counter do banco de dados
        try:
            cursor.execute("SELECT MAX(CAST(SUBSTRING_INDEX(session_id, '_', -1) AS UNSIGNED)) AS max_id FROM logs_testeSite WHERE session_id LIKE 'TestandoSite_%%'")
            result = cursor.fetchone()
            if result and result['max_id'] is not None:
                session_counter = int(result['max_id']) + 1
            else:
                session_counter = 0
        except Exception as e:
            print(f"Aviso: Não foi possível recuperar o último session_id do banco de dados: {e}. Iniciando session_counter em 0.")
            session_counter = 0
        print(f"[init_db] Database initialized. Initial session_counter set to: {session_counter}")

# --- Classe SiteQATester adaptada para ambiente web ---
class SiteQATester:
    def __init__(self, url, modo, session_id=None):
        self.url = url
        self.modo = modo
        self.driver = None
        self.resultados = []
        self.parar = False
        self.session_id = session_id # Para rastrear sessões de teste no servidor
        self.progress = 0
        self.max_progress_steps = 10 # Para modo avançado, ou um valor fixo para rápido

    def _log_progress(self, message, percentage):
        self.progress = percentage
        # Não imprimimos mais aqui, pois web_progress_callback já imprime
        # e faz o log no DB.

    def _log_to_db(self, step, status, response_time=None, message=None, error_message=None):
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO logs_testeSite (session_id, timestamp, step, status, response_time, message, error_message)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''',
                (self.session_id, time.strftime('%Y-%m-%d %H:%M:%S'), step, status, response_time, message, error_message))
                conn.commit()
        except Exception as e:
            print(f"Erro ao logar no banco de dados: {e}")

    def iniciar_driver(self):
        step_name = "Iniciar Driver"
        # O log de "Iniciar Driver" já é feito pelo _log_to_db chamado no rodar_teste
        try:
            chrome_options = Options()
            chrome_options.add_argument("--incognito") 
            # No ambiente web/servidor, o navegador deve ser sempre headless
            chrome_options.add_argument("--headless") 
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--no-sandbox") # Necessário em alguns ambientes de servidor
            chrome_options.add_argument("--disable-dev-shm-usage") # Para evitar problemas de memória em Docker/servidores

            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            # Loga o sucesso após iniciar o driver
            self._log_to_db(step_name, "sucesso", None, "Driver iniciado com sucesso.")
            return True
        except Exception as e:
            self.resultados.append(f"Erro ao iniciar o navegador: {e}")
            self._log_to_db(step_name, "falha", None, f"Erro ao iniciar o navegador: {e}")
            return False

    def fechar_driver(self):
        step_name = "Fechar Driver"
        if self.driver:
            self.driver.quit()
            self.driver = None
            # O log de fechamento do driver será feito no rodar_teste
        else:
            self.resultados.append(f"{step_name}: Driver já estava fechado ou não iniciado.")
            self._log_to_db(step_name, "aviso", None, f"{step_name}: Driver já estava fechado ou não iniciado.")

    def testar_botao(self, elemento):
        try:
            inicio = time.time()
            elemento.click()
            fim = time.time()
            tempo = fim - inicio
            return tempo, None
        except Exception as e:
            try:
                inicio = time.time()
                self.driver.execute_script("arguments[0].click();", elemento)
                fim = time.time()
                tempo = fim - inicio
                self.resultados.append("Tentativa de clique via JavaScript bem-sucedida.")
                return tempo, None
            except Exception as js_e:
                return None, str(e) + " | Erro ao tentar clique JS: " + str(js_e)

    def modo_rapido(self):
        self._log_progress("Iniciando modo rápido...", 0)
        try:
            self.driver.get(self.url)
            time.sleep(2) 

            step_name = "Aceitar Cookies"
            try:
                self.resultados.append(f"{step_name}: Tentando aceitar cookies...")
                aceitar_cookies_btn = self.driver.find_element(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'aceitar')] | //button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]")
                self.driver.execute_script("arguments[0].click();", aceitar_cookies_btn)
                self.resultados.append("Cookies aceitos com sucesso.")
                self._log_to_db(step_name, "sucesso", None, "Cookies aceitos com sucesso.")
                time.sleep(2)
            except NoSuchElementException:
                self.resultados.append("Banner de cookies não encontrado ou já processado.")
                self._log_to_db(step_name, "aviso", None, "Banner de cookies não encontrado ou já processado.")
            except Exception as e:
                self.resultados.append(f"Erro ao tentar aceitar cookies: {e}")
                self._log_to_db(step_name, "falha", None, f"Erro ao tentar aceitar cookies: {e}")

            # Encontra e rola até a seção "Categoria Exemplo"
            self._log_progress("Rolando para a seção 'Categoria Exemplo'...", 25)
            step_name = "Rolar para Seção 'Categoria Exemplo'"
            try:
                self.resultados.append(f"{step_name}: Tentando rolar...")
                napas_section_heading = self.driver.find_element(By.XPATH, "//p[contains(text(), 'Categoria Exemplo')] | //h2[contains(text(), 'Categoria Exemplo')]") # Adicionado <p> para maior compatibilidade
                self.driver.execute_script("arguments[0].scrollIntoView();", napas_section_heading)
                self.resultados.append("Rolado para a seção 'Categoria Exemplo'.")
                self._log_to_db(step_name, "sucesso", None, "Rolado para a seção 'Categoria Exemplo'.")
                time.sleep(2) # Dar tempo para o scroll e elementos carregarem
            except NoSuchElementException:
                self.resultados.append("Erro: Seção 'Categoria Exemplo' não encontrada na página inicial.")
                self._log_to_db(step_name, "falha", None, "Erro: Seção 'Categoria Exemplo' não encontrada na página inicial.")
                return
            except Exception as e:
                self.resultados.append(f"Erro ao rolar para seção 'Categoria Exemplo': {e}")
                self._log_to_db(step_name, "falha", None, f"Erro ao rolar para seção 'Categoria Exemplo': {e}")
                return

            # Clica em um item (produto) dentro da seção "Categoria Exemplo"
            self._log_progress("Clicando no produto da seção 'Categoria Exemplo'...", 40)
            step_name = "Clicar Produto Categoria Exemplo"
            try:
                self.resultados.append(f"{step_name}: Tentando clicar no produto...")
                # XPath corrigido para encontrar links de produtos baseados nas classes VTEX e no padrão de URL.
                produto_napas_link = self.driver.find_element(By.XPATH, "//p[contains(text(), 'Categoria Exemplo')]/ancestor::section[1]//a[contains(@class, 'vtex-product-summary-2-x-clearLink') and contains(@href, '/p')] | //a[contains(@class, 'vtex-product-summary-2-x-clearLink') and contains(@href, '/p')] ")
                tempo, erro = self.testar_botao(produto_napas_link)
                if erro:
                    self.resultados.append(f"Erro ao clicar no produto da seção Categoria Exemplo: {erro}")
                    self._log_to_db(step_name, "falha", tempo, f"Erro ao clicar no produto da seção Categoria Exemplo: {erro}")
                    return
                self.resultados.append(f"Tempo para acessar produto da seção Categoria Exemplo: {tempo:.2f}s")
                self._log_to_db(step_name, "sucesso", tempo, f"Produto da seção Categoria Exemplo acessado em {tempo:.2f}s.")
                time.sleep(2) # Espera a página do produto carregar
            except NoSuchElementException:
                self.resultados.append("Erro: Nenhum link de produto encontrado na seção 'Categoria Exemplo'.")
                self._log_to_db(step_name, "falha", None, "Erro: Nenhum link de produto encontrado na seção 'Categoria Exemplo'.")
                return
            except Exception as e:
                self.resultados.append(f"Erro inesperado ao clicar no produto da seção Categoria Exemplo: {e}")
                self._log_to_db(step_name, "falha", None, f"Erro inesperado ao clicar no produto da seção Categoria Exemplo: {e}")
                return

            self._log_progress("Adicionando produto ao carrinho...", 60)
            step_name = "Adicionar ao Carrinho"
            try:
                self.resultados.append(f"{step_name}: Tentando adicionar produto ao carrinho...")
                print(f"[DEBUG] URL atual antes de buscar o botão Comprar: {self.driver.current_url}") # DEBUG
                wait = WebDriverWait(self.driver, 20) # Aumenta o tempo de espera
                
                # Primeiro, espera que o elemento esteja presente no DOM, depois que esteja clicável
                botao_comprar_locator = (By.XPATH, "//button[.//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'comprar')] or .//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add to cart')]]")
                wait.until(EC.presence_of_element_located(botao_comprar_locator))
                botao_comprar = wait.until(EC.element_to_be_clickable(botao_comprar_locator))
                tempo, erro = self.testar_botao(botao_comprar)
                if erro:
                    self.resultados.append(f"Erro ao clicar em 'Comprar' (adicionar ao carrinho): {erro}")
                    self._log_to_db(step_name, "falha", tempo, f"Erro ao clicar em 'Comprar' (adicionar ao carrinho): {erro}")
                    return
                self.resultados.append(f"Tempo para adicionar produto ao carrinho (clicar em Comprar): {tempo:.2f}s")
                self._log_to_db(step_name, "sucesso", tempo, f"Produto adicionado ao carrinho em {tempo:.2f}s.")
                time.sleep(3)
            except TimeoutException:
                self.resultados.append("Erro de Timeout: Botão 'Comprar' não clicável na página do produto.")
                self._log_to_db(step_name, "falha", None, "Erro de Timeout: Botão 'Comprar' não clicável na página do produto.")
                return
            except NoSuchElementException:
                self.resultados.append("Erro: Botão 'Comprar' (adicionar ao carrinho) não encontrado na página do produto.")
                self._log_to_db(step_name, "falha", None, "Erro: Botão 'Comprar' (adicionar ao carrinho) não encontrado na página do produto.")
                return
            except Exception as e:
                self.resultados.append(f"Erro inesperado ao clicar em 'Comprar': {e}")
                self._log_to_db(step_name, "falha", None, f"Erro inesperado ao clicar em 'Comprar': {e}")
                return

            self._log_progress("Finalizando compra...", 90)
            step_name = "Finalizar Compra"
            try:
                self.resultados.append(f"{step_name}: Tentando finalizar compra...")
                wait = WebDriverWait(self.driver, 10)
                botao_finalizar_compra = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@id='proceed-to-checkout'] | //button[.//div[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ir para o checkout')]]")))
                tempo, erro = self.testar_botao(botao_finalizar_compra)
                if erro:
                    self.resultados.append(f"Erro ao clicar em 'Finalizar compra' no carrinho: {erro}")
                    self._log_to_db(step_name, "falha", tempo, f"Erro ao clicar em 'Finalizar compra' no carrinho: {erro}")
                    return
                self.resultados.append(f"Tempo para finalizar compra e ir para o checkout: {tempo:.2f}s")
                self._log_to_db(step_name, "sucesso", tempo, f"Compra finalizada em {tempo:.2f}s.")
                time.sleep(2)
            except TimeoutException:
                self.resultados.append("Erro de Timeout: Botão 'Finalizar compra' não clicável no carrinho.")
                self._log_to_db(step_name, "falha", None, "Erro de Timeout: Botão 'Finalizar compra' não clicável no carrinho.")
                return
            except NoSuchElementException:
                self.resultados.append("Erro: Botão 'Finalizar compra' não encontrado no carrinho.")
                self._log_to_db(step_name, "falha", None, "Erro: Botão 'Finalizar compra' não encontrado no carrinho.")
                return
            except Exception as e:
                self.resultados.append(f"Erro inesperado ao clicar em 'Finalizar compra': {e}")
                self._log_to_db(step_name, "falha", None, f"Erro inesperado ao clicar em 'Finalizar compra': {e}")
                return

        except Exception as e:
            self.resultados.append(f"Erro no modo rápido: {e}")
            self._log_to_db("Modo Rápido", "falha", None, f"Erro no modo rápido: {e}")
        finally:
            self._log_progress("Modo rápido concluído.", 100)
            self._log_to_db("Modo Rápido", "concluido", None, "Modo rápido concluído.")

    def modo_avancado(self):
        self._log_progress("Iniciando modo avançado...", 0)
        self._log_to_db("Modo Avançado", "iniciado", None, "Iniciando modo avançado...")
        try:
            self.driver.get(self.url)
            time.sleep(2) 

            step_name = "Aceitar Cookies"
            try:
                self.resultados.append(f"{step_name}: Tentando aceitar cookies...")
                aceitar_cookies_btn = self.driver.find_element(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'aceitar')] | //button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]")
                self.driver.execute_script("arguments[0].click();", aceitar_cookies_btn)
                self.resultados.append("Cookies aceitos com sucesso.")
                self._log_to_db(step_name, "sucesso", None, "Cookies aceitos com sucesso.")
                time.sleep(2)
            except NoSuchElementException:
                self.resultados.append("Banner de cookies não encontrado ou já processado.")
                self._log_to_db(step_name, "aviso", None, "Banner de cookies não encontrado ou já processado.")
            except Exception as e:
                self.resultados.append(f"Erro ao tentar aceitar cookies: {e}")
                self._log_to_db(step_name, "falha", None, f"Erro ao tentar aceitar cookies: {e}")

            produtos_adicionados = 0
            urls_produtos_visitados = set()

            while produtos_adicionados < 10:
                self._log_progress(f"Adicionando produto {produtos_adicionados + 1} de 10...", produtos_adicionados * 9)
                current_product_step_name = f"Adicionar Produto {produtos_adicionados + 1} de 10"
                try:
                    elementos_slider_links = self.driver.find_elements(By.XPATH, "//section[.//p[contains(@class, 'vtex-rich-text')] or .//h2]//a[contains(@class, 'vtex-product-summary-2-x-clearLink') and contains(@href, '/p')]")
                    elementos_nao_visitados = [el for el in elementos_slider_links if el.get_attribute('href') not in urls_produtos_visitados]

                    if not elementos_nao_visitados:
                        self.resultados.append("Aviso: Não há mais produtos novos em sliders na home. Tentando recarregar a página...")
                        self._log_to_db(current_product_step_name, "aviso", None, "Não há mais produtos novos em sliders na home. Tentando recarregar a página...")
                        self.driver.get(self.url) # Recarrega a homepage
                        time.sleep(3) # Espera a página carregar
                        # Tenta encontrar produtos novamente após recarregar
                        elementos_slider_links = self.driver.find_elements(By.XPATH, "//section[.//p[contains(@class, 'vtex-rich-text')] or .//h2]//a[contains(@class, 'vtex-product-summary-2-x-clearLink') and contains(@href, '/p')]")
                        elementos_nao_visitados = [el for el in elementos_slider_links if el.get_attribute('href') not in urls_produtos_visitados]
                        if not elementos_nao_visitados: # Se ainda não encontrar, então não há mais produtos
                            self.resultados.append("Não há mais produtos novos mesmo após recarregar a página.")
                            self._log_to_db(current_product_step_name, "aviso", None, "Não há mais produtos novos mesmo após recarregar a página.")
                            break # Sai do loop se não encontrar novos produtos após recarregar
                        else:
                            continue # Continua o loop para processar os novos produtos encontrados
                    
                    produto_link = elementos_nao_visitados[0]
                    produto_url = produto_link.get_attribute('href')
                    urls_produtos_visitados.add(produto_url)

                    self.driver.execute_script("arguments[0].scrollIntoView();", produto_link)
                    tempo, erro = self.testar_botao(produto_link)
                    if erro:
                        self.resultados.append(f"Erro ao clicar no produto: {erro}")
                        self._log_to_db(current_product_step_name, "falha", tempo, f"Erro ao clicar no produto: {erro}")
                        continue
                    self.resultados.append(f"Tempo para acessar produto {produtos_adicionados+1}: {tempo:.2f}s")
                    self._log_to_db(current_product_step_name, "sucesso", tempo, f"Produto {produtos_adicionados+1} acessado em {tempo:.2f}s.")
                    time.sleep(2)

                    try:
                        add_to_cart_step_name = f"Adicionar Produto {produtos_adicionados+1} ao Carrinho"
                        wait = WebDriverWait(self.driver, 20) # Aumenta o tempo de espera
                        print(f"[DEBUG - Modo Avançado] URL atual antes de buscar o botão Comprar: {self.driver.current_url}") # DEBUG
                        
                        # Primeiro, espera que o elemento esteja presente no DOM, depois que esteja clicável
                        botao_comprar_locator = (By.XPATH, "//button[.//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'comprar')] or .//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add to cart')]]")
                        wait.until(EC.presence_of_element_located(botao_comprar_locator))
                        botao_comprar = wait.until(EC.element_to_be_clickable(botao_comprar_locator))
                        
                        tempo_comprar, erro_comprar = self.testar_botao(botao_comprar)
                        if erro_comprar:
                            self.resultados.append(f"Erro ao clicar em 'Comprar' para adicionar ao carrinho: {erro_comprar}")
                            self._log_to_db(add_to_cart_step_name, "falha", tempo_comprar, f"Erro ao clicar em 'Comprar' para adicionar ao carrinho: {erro_comprar}")
                        else:
                            self.resultados.append(f"Tempo para adicionar produto {produtos_adicionados+1} ao carrinho: {tempo_comprar:.2f}s")
                            self._log_to_db(add_to_cart_step_name, "sucesso", tempo_comprar, f"Produto {produtos_adicionados+1} adicionado ao carrinho em {tempo_comprar:.2f}s.")
                            produtos_adicionados += 1
                            self._log_progress(f"Produto {produtos_adicionados} adicionado ao carrinho.", produtos_adicionados * 9)

                        time.sleep(3)

                    except TimeoutException:
                        self.resultados.append(f"Erro de Timeout: Botão 'Comprar' não clicável na página do produto {produto_url}.")
                        self._log_to_db(add_to_cart_step_name, "falha", None, f"Erro de Timeout: Botão 'Comprar' não clicável na página do produto {produto_url}.")
                    except NoSuchElementException:
                        self.resultados.append(f"Erro: Botão 'Comprar' não encontrado na página do produto {produto_url}.")
                        self._log_to_db(add_to_cart_step_name, "falha", None, f"Erro: Botão 'Comprar' não encontrado na página do produto {produto_url}.")
                    except Exception as e:
                        self.resultados.append(f"Erro inesperado ao adicionar ao carrinho para {produto_url}: {e}")
                        self._log_to_db(add_to_cart_step_name, "falha", None, f"Erro inesperado ao adicionar ao carrinho para {produto_url}: {e}")

                except Exception as e:
                    self.resultados.append(f"Erro ao processar produto no modo avançado: {e}")
                    self._log_to_db(current_product_step_name, "falha", None, f"Erro ao processar produto no modo avançado: {e}")
                    self.driver.get(self.url)
                    time.sleep(3)
                    
            if produtos_adicionados == 0:
                self.resultados.append("Nenhum produto foi adicionado ao carrinho no modo avançado.")
                self._log_to_db("Modo Avançado", "aviso", None, "Nenhum produto foi adicionado ao carrinho no modo avançado.")
                self._log_progress("Modo avançado concluído (sem produtos adicionados).", 100)
                return

            self._log_progress("Finalizando compra...", 95)
            step_name = "Finalizar Compra (Modo Avançado)"
            try:
                self.resultados.append(f"{step_name}: Tentando finalizar compra...")
                wait = WebDriverWait(self.driver, 10)
                botao_finalizar_compra = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@id='proceed-to-checkout'] | //button[.//div[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ir para o checkout')]]")))
                tempo, erro = self.testar_botao(botao_finalizar_compra)
                if erro:
                    self.resultados.append(f"Erro ao clicar em 'Finalizar compra' no carrinho (modo avançado): {erro}")
                    self._log_to_db(step_name, "falha", tempo, f"Erro ao clicar em 'Finalizar compra' no carrinho (modo avançado): {erro}")
                    return
                self.resultados.append(f"Tempo para finalizar compra e ir para o checkout com {produtos_adicionados} itens: {tempo:.2f}s")
                self._log_to_db(step_name, "sucesso", tempo, f"Compra finalizada em {tempo:.2f}s com {produtos_adicionados} itens.")
                time.sleep(2)
            except TimeoutException:
                self.resultados.append("Erro de Timeout: Botão 'Finalizar compra' não clicável no carrinho (modo avançado).")
                self._log_to_db(step_name, "falha", None, "Erro de Timeout: Botão 'Finalizar compra' não clicável no carrinho (modo avançado).")
            except NoSuchElementException:
                self.resultados.append("Erro: Botão 'Finalizar compra' não encontrado no carrinho (modo avançado).")
                self._log_to_db(step_name, "falha", None, "Erro: Botão 'Finalizar compra' não encontrado no carrinho (modo avançado).")
            except Exception as e:
                self.resultados.append(f"Erro inesperado ao clicar em 'Finalizar compra' (modo avançado): {e}")
                self._log_to_db(step_name, "falha", None, f"Erro inesperado ao clicar em 'Finalizar compra' (modo avançado): {e}")
        finally:
            self._log_progress("Modo avançado concluído.", 100)
            self._log_to_db("Modo Avançado", "concluido", None, "Modo avançado concluído.")

    def rodar_teste(self):
        self.resultados.clear()
        self.progress = 0
        self._log_progress("Iniciando driver...", 5)
        # O log de "Iniciar Driver" já é feito dentro de iniciar_driver()
        if not self.iniciar_driver():
            self._log_progress("Falha ao iniciar driver.", 100)
            # O log de falha ao iniciar driver já é feito dentro de iniciar_driver()
            return
        try:
            # Removido o log duplicado, o progresso inicial será gerado pelo web_progress_callback
            if self.modo == "Rápida":
                self.modo_rapido()
            else:
                self.modo_avancado()
        except WebDriverException as e:
            self.resultados.append(f"Erro de WebDriver: {e}")
            self._log_to_db("Execução do Teste", "falha", None, f"Erro de WebDriver: {e}")
        except Exception as e:
            self.resultados.append(f"Erro inesperado: {e}")
            self._log_to_db("Execução do Teste", "falha", None, f"Erro inesperado: {e}")
        finally:
            self.fechar_driver()
            self._log_progress("Driver fechado.", 100)
            self._log_to_db("Fechar Driver", "concluido", None, "Driver fechado.")

# --- Configuração do Flask ---
app = Flask(__name__)
# Armazenamento temporário para resultados de testes em andamento
# Em produção, usaria um banco de dados ou sistema de cache (Redis)
test_sessions = {}
session_lock = threading.Lock()
init_db() # Inicializa o banco de dados na inicialização da aplicação

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_test', methods=['POST'])
def start_test():
    with session_lock:
        global session_counter
        session_counter += 1
        session_id = f"TestandoSite_{session_counter}"
    print(f"[start_test] Gerado session_id: {session_id}")

    data = request.get_json() # Pega os dados JSON da requisição

    url = data['url']
    modo = data['modo']
    
    # Criar uma nova instância do SiteQATester para esta sessão
    tester = SiteQATester(url, modo, session_id=session_id)
    
    # Armazenar o objeto tester (e, portanto, os resultados e progresso) por session_id
    test_sessions[session_id] = {
        'tester': tester,
        'status': 'running',
        'results': [],
        'progress': 0,
        'start_time': time.time(),
        'end_time': None
    }

    def run_test_in_background():
        local_tester = test_sessions[session_id]['tester']
        def web_progress_callback(message, percentage):
            current_session = test_sessions[session_id]
            current_session['progress'] = percentage
            # Não imprima aqui, pois o log já é feito no _log_to_db que é chamado logo em seguida
            
            # Logar a mensagem de progresso no banco de dados como um passo intermediário
            local_tester._log_to_db(step=message, status="em_progresso", message=message, response_time=None, error_message=None)
            
            # Buscar os logs mais recentes do banco de dados para a sessão
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT step, status, response_time, error_message, message FROM logs_testeSite WHERE session_id = %s ORDER BY timestamp ASC", (session_id,))
                current_session['results'] = [dict(row) for row in cursor.fetchall()]
            print(f"[web_progress_callback] Logs recebidos para {session_id}: {current_session['results']}") # DEBUG
        
        local_tester._log_progress = web_progress_callback # Sobrescreve o método de log para usar o callback da web
        
        local_tester.rodar_teste()
        
        test_sessions[session_id]['status'] = 'completed'
        test_sessions[session_id]['end_time'] = time.time()

    # Iniciar o teste em uma thread separada para não bloquear a requisição web
    thread = threading.Thread(target=run_test_in_background)
    thread.daemon = True # Permite que a thread termine com a aplicação principal
    thread.start()

    return jsonify({'status': 'Test initiated', 'session_id': session_id})

@app.route('/status/<session_id>')
def test_status(session_id):
    session_data = test_sessions.get(session_id)
    if not session_data:
        return jsonify({'error': 'Session not found'}), 404
    
    print(f"[test_status] Retornando status para {session_id}, Progress: {session_data['progress']}%, Results count: {len(session_data['results'])}")
    # Retornar uma cópia dos resultados para evitar modificações enquanto a thread está rodando
    return jsonify({
        'status': session_data['status'],
        'progress': session_data['progress'],
        'results': session_data['results']
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
