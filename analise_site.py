import time
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException, NoSuchElementException, TimeoutException
import tkinter as tk
from tkinter import ttk, messagebox
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

class SiteQATester:
    def __init__(self, url, modo, intervalo, verificacao_assistida, progress_callback=None):
        self.url = url
        self.modo = modo
        self.intervalo = intervalo  # em horas
        self.verificacao_assistida = verificacao_assistida
        self.driver = None
        self.resultados = []
        self.parar = False
        self.progress_callback = progress_callback # Adiciona o callback de progresso

    def iniciar_driver(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument("--incognito") # Adiciona o argumento para modo anônimo
            
            if self.verificacao_assistida == "Off":
                chrome_options.add_argument("--headless") # Inicia o navegador em modo headless (sem interface gráfica)
                chrome_options.add_argument("--disable-gpu") # Necessário para headless no Windows
                chrome_options.add_argument("--window-size=1920,1080") # Define um tamanho de janela para headless

            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao iniciar o navegador: {e}")
            return False
        return True

    def fechar_driver(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def testar_botao(self, elemento):
        try:
            inicio = time.time()
            elemento.click() # Tenta o clique nativo do Selenium
            fim = time.time()
            tempo = fim - inicio
            return tempo, None
        except Exception as e:
            # Se o clique nativo falhar, tenta clicar via JavaScript
            try:
                inicio = time.time()
                self.driver.execute_script("arguments[0].click();", elemento)
                fim = time.time()
                tempo = fim - inicio
                self.resultados.append("Tentativa de clique via JavaScript bem-sucedida.") # Para depuração
                return tempo, None
            except Exception as js_e:
                return None, str(e) + " | Erro ao tentar clique JS: " + str(js_e)

    def modo_rapido(self):
        try:
            self.driver.get(self.url)
            time.sleep(2) # Dar tempo para a página carregar e o banner de cookies aparecer

            # Tenta aceitar o banner de cookies se ele aparecer
            try:
                # O XPath tenta encontrar um botão com 'aceitar' ou 'accept' (case insensitive)
                aceitar_cookies_btn = self.driver.find_element(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'aceitar')] | //button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]")
                self.driver.execute_script("arguments[0].click();", aceitar_cookies_btn)
                self.resultados.append("Cookies aceitos com sucesso.")
                time.sleep(2)
            except NoSuchElementException:
                self.resultados.append("Banner de cookies não encontrado ou já processado.")
            except Exception as e:
                self.resultados.append(f"Erro ao tentar aceitar cookies: {e}")
                # Não retornamos aqui, pois o script pode continuar mesmo que os cookies não sejam aceitos

            # Encontra e rola até a seção "Categoria Exemplo"
            try:
                # Em um cenário real, você buscaria por categorias específicas do seu site
                napas_section_heading = self.driver.find_element(By.XPATH, "//p[contains(text(), 'Categoria Exemplo')] | //h2[contains(text(), 'Categoria Exemplo')]") # Adicionado <p> para maior compatibilidade
                self.driver.execute_script("arguments[0].scrollIntoView();", napas_section_heading)
                self.resultados.append("Rolado para a seção 'Categoria Exemplo'.")
                if self.progress_callback: self.progress_callback(25) # Atualiza progresso
                time.sleep(2) # Dar tempo para o scroll e elementos carregarem
            except NoSuchElementException:
                self.resultados.append("Erro: Seção 'Categoria Exemplo' não encontrada na página inicial.")
                return
            except Exception as e:
                self.resultados.append(f"Erro ao rolar para seção 'Categoria Exemplo': {e}")
                return

            # Clica em um item (produto) dentro da seção "Categoria Exemplo"
            try:
                # XPath corrigido para encontrar links de produtos baseados nas classes VTEX e no padrão de URL.
                produto_napas_link = self.driver.find_element(By.XPATH, "//p[contains(text(), 'Categoria Exemplo')]/ancestor::section[1]//a[contains(@class, 'vtex-product-summary-2-x-clearLink') and contains(@href, '/p')]")
                if self.progress_callback: self.progress_callback(40) # Atualiza progresso
                tempo, erro = self.testar_botao(produto_napas_link)
                if erro:
                    self.resultados.append(f"Erro ao clicar no produto da seção Categoria Exemplo: {erro}")
                    return
                self.resultados.append(f"Tempo para acessar produto da seção Categoria Exemplo: {tempo:.2f}s")
                time.sleep(2) # Espera a página do produto carregar
            except NoSuchElementException:
                self.resultados.append("Erro: Nenhum link de produto encontrado na seção 'Categoria Exemplo'.")
                return
            except Exception as e:
                self.resultados.append(f"Erro inesperado ao clicar no produto da seção Categoria Exemplo: {e}")
                return

            # Clica no botão "Comprar" (para adicionar ao carrinho) na página do produto
            try:
                # Usando WebDriverWait para esperar que o botão "Comprar" esteja clicável
                wait = WebDriverWait(self.driver, 10) # Espera até 10 segundos
                botao_comprar = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'comprar')] or .//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add to cart')]]")))
                if self.progress_callback: self.progress_callback(60) # Atualiza progresso
                tempo, erro = self.testar_botao(botao_comprar)
                if erro:
                    self.resultados.append(f"Erro ao clicar em 'Comprar' (adicionar ao carrinho): {erro}")
                    return
                self.resultados.append(f"Tempo para adicionar produto ao carrinho (clicar em Comprar): {tempo:.2f}s")
                time.sleep(3) # Tempo para o carrinho abrir automaticamente
            except TimeoutException:
                self.resultados.append("Erro de Timeout: Botão 'Comprar' não clicável na página do produto.")
                return
            except NoSuchElementException:
                self.resultados.append("Erro: Botão 'Comprar' (adicionar ao carrinho) não encontrado na página do produto.")
                return
            except Exception as e:
                self.resultados.append(f"Erro inesperado ao clicar em 'Comprar': {e}")
                return

            # No carrinho, clica em "Finalizar compra"
            try:
                # Usando WebDriverWait para esperar que o botão "Ir para o checkout" esteja clicável
                wait = WebDriverWait(self.driver, 10) # Espera até 10 segundos
                botao_finalizar_compra = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@id='proceed-to-checkout'] | //button[.//div[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ir para o checkout')]]")))

                tempo, erro = self.testar_botao(botao_finalizar_compra)
                if erro:
                    self.resultados.append(f"Erro ao clicar em 'Finalizar compra' no carrinho: {erro}")
                    return
                self.resultados.append(f"Tempo para finalizar compra e ir para o checkout: {tempo:.2f}s")
                time.sleep(2)
                if self.progress_callback: self.progress_callback(100) # Finaliza progresso
            except TimeoutException:
                self.resultados.append("Erro de Timeout: Botão 'Finalizar compra' não clicável no carrinho.")
                return
            except NoSuchElementException:
                self.resultados.append("Erro: Botão 'Finalizar compra' não encontrado no carrinho.")
                return
            except Exception as e:
                self.resultados.append(f"Erro inesperado ao clicar em 'Finalizar compra': {e}")
                return

        except Exception as e:
            self.resultados.append(f"Erro no modo rápido: {e}")

    def modo_avancado(self):
        try:
            self.driver.get(self.url)
            time.sleep(2) # Dar tempo para a página carregar e o banner de cookies aparecer

            # Tenta aceitar o banner de cookies se ele aparecer
            try:
                aceitar_cookies_btn = self.driver.find_element(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'aceitar')] | //button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]")
                self.driver.execute_script("arguments[0].click();", aceitar_cookies_btn)
                self.resultados.append("Cookies aceitos com sucesso.")
                time.sleep(2)
            except NoSuchElementException:
                self.resultados.append("Banner de cookies não encontrado ou já processado.")
            except Exception as e:
                self.resultados.append(f"Erro ao tentar aceitar cookies: {e}")

            # Encontra e rola até a seção "Categoria Exemplo"
            try:
                napas_section_heading = self.driver.find_element(By.XPATH, "//p[contains(text(), 'Categoria Exemplo')] | //h2[contains(text(), 'Categoria Exemplo')]") # Adicionado <p> para maior compatibilidade
                self.driver.execute_script("arguments[0].scrollIntoView();", napas_section_heading)
                self.resultados.append("Rolado para a seção 'Categoria Exemplo'.")
                time.sleep(2)
            except NoSuchElementException:
                self.resultados.append("Erro: Seção 'Categoria Exemplo' não encontrada na página inicial. Tentando encontrar produtos em outras seções de slider.")
                # Não retornamos aqui, para tentar encontrar produtos em outras seções
            except Exception as e:
                self.resultados.append(f"Erro ao rolar para seção 'Categoria Exemplo': {e}. Tentando encontrar produtos em outras seções de slider.")
                # Não retornamos aqui, para tentar encontrar produtos em outras seções

            if self.progress_callback: self.progress_callback(0) # Inicia o progresso

            produtos_adicionados = 0
            urls_produtos_visitados = set()

            while produtos_adicionados < 10:
                try:
                    elementos_slider_links = self.driver.find_elements(By.XPATH, "//section[.//p[contains(@class, 'vtex-rich-text')] or .//h2]//a[contains(@class, 'vtex-product-summary-2-x-clearLink') and contains(@href, '/p')]")
                    elementos_nao_visitados = [el for el in elementos_slider_links if el.get_attribute('href') not in urls_produtos_visitados]

                    if not elementos_nao_visitados:
                        self.resultados.append("Não há mais produtos novos em nenhuma seção de slider na home para adicionar ao carrinho.")
                        break
                    
                    produto_link = elementos_nao_visitados[0]
                    produto_url = produto_link.get_attribute('href')
                    urls_produtos_visitados.add(produto_url)

                    self.driver.execute_script("arguments[0].scrollIntoView();", produto_link)
                    tempo, erro = self.testar_botao(produto_link) # Clica no link do produto
                    if erro:
                        self.resultados.append(f"Erro ao clicar no produto: {erro}")
                        self.driver.get(self.url)
                        time.sleep(2)
                        continue
                    self.resultados.append(f"Tempo para acessar produto {produtos_adicionados+1}: {tempo:.2f}s")
                    time.sleep(2)

                    try:
                        wait = WebDriverWait(self.driver, 10)
                        botao_comprar = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'comprar')] or .//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add to cart')]]")))
                        
                        tempo_comprar, erro_comprar = self.testar_botao(botao_comprar)
                        if erro_comprar:
                            self.resultados.append(f"Erro ao clicar em 'Comprar' para adicionar ao carrinho: {erro_comprar}")
                        else:
                            self.resultados.append(f"Tempo para adicionar produto {produtos_adicionados+1} ao carrinho: {tempo_comprar:.2f}s")
                            produtos_adicionados += 1
                            if self.progress_callback: self.progress_callback(produtos_adicionados * 9) # Atualiza progresso (90% para 10 itens)

                        time.sleep(3)

                    except TimeoutException:
                        self.resultados.append(f"Erro de Timeout: Botão 'Comprar' não clicável na página do produto {produto_url}.")
                    except NoSuchElementException:
                        self.resultados.append(f"Erro: Botão 'Comprar' não encontrado na página do produto {produto_url}.")
                    except Exception as e:
                        self.resultados.append(f"Erro inesperado ao adicionar ao carrinho para {produto_url}: {e}")

                    if produtos_adicionados < 10 and elementos_nao_visitados[1:]:
                        self.driver.get(self.url)
                        time.sleep(3)

                        try:
                            napas_section_heading = self.driver.find_element(By.XPATH, "//p[contains(text(), 'Categoria Exemplo')] | //h2[contains(text(), 'Categoria Exemplo')]")
                            self.driver.execute_script("arguments[0].scrollIntoView();", napas_section_heading)
                            time.sleep(1)
                        except Exception as e_scroll:
                            self.resultados.append(f"Aviso: Não foi possível rolar para a seção Categoria Exemplo após voltar para home: {e_scroll}")

                except Exception as e:
                    self.resultados.append(f"Erro ao processar produto no modo avançado: {e}")
                    self.driver.get(self.url)
                    time.sleep(3)
                    
            if produtos_adicionados == 0:
                self.resultados.append("Nenhum produto foi adicionado ao carrinho no modo avançado.")
                if self.progress_callback: self.progress_callback(100) # Finaliza progresso mesmo sem itens
                return

            # Agora vamos para o checkout com os itens que foram adicionados
            try:
                wait = WebDriverWait(self.driver, 10)
                botao_finalizar_compra = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@id='proceed-to-checkout'] | //button[.//div[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ir para o checkout')]]")))
                if self.progress_callback: self.progress_callback(95) # Atualiza progresso
                tempo, erro = self.testar_botao(botao_finalizar_compra)
                if erro:
                    self.resultados.append(f"Erro ao clicar em 'Finalizar compra' no carrinho (modo avançado): {erro}")
                    return
                self.resultados.append(f"Tempo para finalizar compra e ir para o checkout com {produtos_adicionados} itens: {tempo:.2f}s")
                time.sleep(2)
                if self.progress_callback: self.progress_callback(100) # Finaliza progresso
            except TimeoutException:
                self.resultados.append("Erro de Timeout: Botão 'Finalizar compra' não clicável no carrinho (modo avançado).")
            except NoSuchElementException:
                self.resultados.append("Erro: Botão 'Finalizar compra' não encontrado no carrinho (modo avançado).")
            except Exception as e:
                self.resultados.append(f"Erro inesperado ao clicar em 'Finalizar compra' (modo avançado): {e}")

        except Exception as e:
            self.resultados.append(f"Erro no modo avançado: {e}")

    def rodar_teste(self):
        self.resultados.clear()
        if not self.iniciar_driver():
            return
        try:
            if self.modo == "Rápida":
                self.modo_rapido()
            else:
                self.modo_avancado()
        except WebDriverException as e:
            self.resultados.append(f"Erro de WebDriver: {e}")
        except Exception as e:
            self.resultados.append(f"Erro inesperado: {e}")
        finally:
            self.fechar_driver()

    def monitorar(self, callback_resultado):
        while not self.parar:
            self.rodar_teste()
            callback_resultado(self.resultados)
            for _ in range(int(self.intervalo * 3600)):
                if self.parar:
                    break
                time.sleep(1)

class AppQA(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("QA Automático de E-commerce")
        self.geometry("500x400")
        self.tester = None
        self.thread = None

        # Configurações
        tk.Label(self, text="URL do site:").pack(pady=5)
        self.url_entry = tk.Entry(self, width=60)
        self.url_entry.pack(pady=5)
        self.url_entry.insert(0, "https://www.exemplo-ecommerce.com.br")
        self.url_entry.config(state="readonly") # Torna o campo de URL somente leitura

        tk.Label(self, text="Modo de leitura:").pack(pady=5)
        self.modo_var = tk.StringVar(value="Rápida")
        modos = ["Rápida", "Avançada"]
        self.modo_combo = ttk.Combobox(self, textvariable=self.modo_var, values=modos, state="readonly")
        self.modo_combo.pack(pady=5)

        tk.Label(self, text="Intervalo de teste:").pack(pady=5)
        self.intervalo_var = tk.StringVar(value="1")
        self.intervalo_combo = ttk.Combobox(self, textvariable=self.intervalo_var, values=["1", "12", "24"], state="readonly")
        self.intervalo_combo.pack(pady=5)
        tk.Label(self, text="(em horas)").pack()

        # Nova configuração: Verificação Assistida
        tk.Label(self, text="Verificação Assistida:").pack(pady=5)
        self.verificacao_assistida_var = tk.StringVar(value="On")
        verificacao_options = ["On", "Off"]
        self.verificacao_assistida_combo = ttk.Combobox(self, textvariable=self.verificacao_assistida_var, values=verificacao_options, state="readonly")
        self.verificacao_assistida_combo.pack(pady=5)

        self.resultado_text = tk.Text(self, height=10, width=60)
        self.resultado_text.pack(pady=10)

        # Barra de progresso (inicialmente oculta)
        self.progressbar = ttk.Progressbar(self, orient="horizontal", length=400, mode="determinate")
        self.progressbar.pack(pady=5)
        self.progressbar.pack_forget() # Esconde inicialmente

        self.iniciar_btn = tk.Button(self, text="Iniciar Monitoramento", command=self.iniciar_monitoramento)
        self.iniciar_btn.pack(pady=5)
        self.parar_btn = tk.Button(self, text="Parar Monitoramento", command=self.parar_monitoramento, state="disabled")
        self.parar_btn.pack(pady=5)

    def mostrar_resultados(self, resultados):
        self.resultado_text.delete(1.0, tk.END)
        for r in resultados:
            self.resultado_text.insert(tk.END, r + "\n")
        if any("Erro" in r for r in resultados):
            messagebox.showwarning("Alerta", "Algum link ou função do site está fora do ar!")

    def iniciar_monitoramento(self):
        url = self.url_entry.get()
        modo = self.modo_var.get()
        intervalo = float(self.intervalo_var.get())
        verificacao_assistida = self.verificacao_assistida_var.get()
        
        if verificacao_assistida == "Off":
            self.progressbar.pack(pady=5)
            self.progressbar['value'] = 0
            progress_callback = self.atualizar_progresso
        else:
            self.progressbar.pack_forget()
            progress_callback = None

        self.tester = SiteQATester(url, modo, intervalo, verificacao_assistida, progress_callback)
        self.iniciar_btn.config(state="disabled")
        self.parar_btn.config(state="normal")
        self.thread = threading.Thread(target=self.tester.monitorar, args=(self.mostrar_resultados,), daemon=True)
        self.thread.start()

    def parar_monitoramento(self):
        if self.tester:
            self.tester.parar = True
        self.iniciar_btn.config(state="normal")
        self.parar_btn.config(state="disabled")
        self.resultado_text.insert(tk.END, "Monitoramento parado pelo usuário.\n")

    def atualizar_progresso(self, valor):
        self.progressbar['value'] = valor
        self.update_idletasks() # Força a atualização da GUI

if __name__ == "__main__":
    app = AppQA()
    app.mainloop()
