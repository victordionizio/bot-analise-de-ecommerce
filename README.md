# QA Automático para E-commerce

Este projeto é uma ferramenta de automação de Quality Assurance (QA) desenvolvida para testar fluxos críticos de e-commerce, como navegação por categorias, adição de produtos ao carrinho e checkout. Ele utiliza **Selenium WebDriver** para simular interações de usuários e **Flask** para fornecer uma interface web de controle e monitoramento.

## 📋 Funcionalidades

-   **Monitoramento via Interface Gráfica e Web**: Interface desktop (Tkinter) e Web (Flask) para iniciar e acompanhar testes.
-   **Testes Automatizados (Selenium)**:
    -   Navegação na Homepage.
    -   Aceite de Cookies.
    -   Busca e acesso a produtos em categorias específicas (configurável).
    -   Adição de produtos ao carrinho.
    -   Simulação de checkout.
-   **Modos de Teste**:
    -   **Rápido**: Executa um fluxo simples de compra de um item.
    -   **Avançado**: Adiciona múltiplos itens ao carrinho para teste de carga e robustez.
-   **Registro de Logs**: Armazena o histórico de testes e métricas de performance em banco de dados.

## 🚀 Tecnologias Utilizadas

-   **Python 3.x**
-   **Selenium WebDriver**: Automação do navegador.
-   **Flask**: Backend da interface web.
-   **Tkinter**: Interface gráfica desktop (para execução local offline).
-   **PyMySQL**: Conexão com banco de dados MySQL para logs.

## 📦 Pré-requisitos

1.  **Python Instalado**: Certifique-se de ter o Python 3 instalado.
2.  **Google Chrome**: O navegador deve estar instalado.
3.  **ChromeDriver**: O driver compatível com sua versão do Chrome deve estar no PATH do sistema.

## 🔧 Instalação

1.  Clone o repositório:
    ```bash
    git clone https://github.com/seu-usuario/qa-automatico-ecommerce.git
    cd qa-automatico-ecommerce
    ```

2.  Crie um ambiente virtual (recomendado):
    ```bash
    python -m venv venv
    source venv/bin/activate  # No Windows: venv\Scripts\activate
    ```

3.  Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```

## ⚙️ Configuração

Antes de rodar, é necessário configurar as credenciais do banco de dados e URLs alvo, pois o código foi anonimizado para este repositório.

1.  **Banco de Dados**:
    Abra o arquivo `web_analise_site.py` e edite a função `get_db_connection` com suas credenciais MySQL:
    ```python
    def get_db_connection():
        conn = pymysql.connect(host='localhost', # Seu Host
                               user='seu_usuario', # Seu Usuário
                               password='sua_senha', # Sua Senha
                               database='seu_banco', # Seu Banco
                               cursorclass=pymysql.cursors.DictCursor)
        return conn
    ```

2.  **Alvo do Teste**:
    Nos arquivos `analise_site.py` e `web_analise_site.py`, ajuste os XPaths e nomes de categorias ("Categoria Exemplo") para corresponderem ao e-commerce que deseja testar. O padrão atual é genérico.

## ▶️ Como Executar

### Interface Web (Recomendado)
Para iniciar a aplicação web:
```bash
python web_analise_site.py
```
Acesse `http://localhost:5000` no seu navegador.

### Interface Desktop
Para iniciar a versão desktop:
```bash
python analise_site.py
```

## 🛡️ Aviso Legal

Este projeto foi desenvolvido para fins educacionais e de portfólio. Certifique-se de ter permissão para executar testes automatizados no site alvo.

---
**Desenvolvido por [Seu Nome]**
