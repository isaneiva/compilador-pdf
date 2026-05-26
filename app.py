import streamlit as st
import openpyxl
import requests
from PyPDF2 import PdfMerger
import io

st.set_page_config(page_title="Compilador de PDFs", page_icon="📄")
st.title("Compilador de PDFs 📄")

# Recebe o arquivo Excel
arquivo_excel = st.file_uploader("Faça o upload da planilha com os links", type=["xlsx"])

if arquivo_excel is not None:
    
    # 1. Verifica se o PDF JÁ FOI processado e está na memória
    if "pdf_pronto" not in st.session_state:
        
        # Inicia a leitura do Excel
        wb = openpyxl.load_workbook(arquivo_excel, data_only=True)
        ws = wb.active

        urls = []
        for row in ws.iter_rows(min_row=2, min_col=2, max_col=2):
            cell = row[0]
            if cell.hyperlink and cell.hyperlink.target:
                urls.append(cell.hyperlink.target)
            else:
                val = cell.value
                if isinstance(val, str) and val.strip().lower().startswith('http'):
                    urls.append(val.strip())
        
        st.success(f'Encontradas {len(urls)} URLs para download.')

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'application/pdf',
            'Referer': 'https://www.camara.leg.br/'
        }

        arquivos_memoria = [] # Lista apenas para os arquivos virtuais
        total_arquivos = len(urls)
        
        # Inicia a barra de progresso
        barra_progresso = st.progress(0.0)
        
        with st.spinner("Baixando e processando os arquivos... ⏳"):
            for i, url in enumerate(urls):
                try:
                    resp = requests.get(url, headers=headers, timeout=15)
                    resp.raise_for_status()
                    
                    # Cria o arquivo virtual na memória e salva na lista (sem usar 'open()')
                    pdf_virtual = io.BytesIO(resp.content)
                    arquivos_memoria.append(pdf_virtual)
                    
                except requests.exceptions.RequestException as e:
                    st.error(f'Erro ao baixar {url}: {e}')

                # Atualiza a barra de progresso
                barra_progresso.progress((i + 1) / total_arquivos)

        # Trava de segurança validando a nova lista
        if not arquivos_memoria:
            st.error('Nenhum PDF válido foi baixado. Verifique as URLs na planilha.')
            st.stop()

        # Mesclagem usando os arquivos da memória
        merger = PdfMerger()
        for arquivo in arquivos_memoria:
            merger.append(arquivo)

        pdf_final_memoria = io.BytesIO()
        merger.write(pdf_final_memoria)
        merger.close()
        pdf_final_memoria.seek(0)
        
        # Salva o resultado final na memória do Streamlit
        st.session_state["pdf_pronto"] = pdf_final_memoria

    # 2. Exibe o botão de download usando o arquivo salvo na memória
    st.success("🎉 PDF compilado com sucesso!")
    
    nome_original = arquivo_excel.name.replace(".xlsx", "")
    nome_final = f"{nome_original}_compilado.pdf"

    st.download_button(
        label="Clique aqui para baixar o PDF compilado",
        data=st.session_state["pdf_pronto"],
        file_name=nome_final,
        mime="application/pdf"
    )
    
    # 3. Validação com o usuário
    st.write("---")
    st.write("Seu documento foi baixado corretamente?")
    
    col1, col2 = st.columns(2)

    if col1.button("Sim"):
        st.success("Processo encerrado! Você pode fechar esta página ou enviar uma nova planilha.")
        
    if col2.button("Não"):
        st.warning("Ok, vamos refazer o processo de leitura e compilação para você!")
        # Apaga o PDF da memória e força a página a recarregar para recomeçar o processo
        del st.session_state["pdf_pronto"]
        st.rerun()