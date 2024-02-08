import pdfplumber
import pandas as pd
import numpy as np
#import math
import streamlit as st
#import plotly.express as px
import plotly.graph_objects as go

# Função para mapear os meses abreviados para seus equivalentes em inglês
def mapear_meses(mes_abreviado):
    meses_mapping = {
        'JAN': 'JAN',
        'FEV': 'FEB',
        'MAR': 'MAR',
        'ABR': 'APR',
        'MAI': 'MAY',
        'JUN': 'JUN',
        'JUL': 'JUL',
        'AGO': 'AUG',
        'SET': 'SEP',
        'OUT': 'OCT',
        'NOV': 'NOV',
        'DEZ': 'DEC',
    }
    return meses_mapping.get(mes_abreviado, mes_abreviado)

# Função para extrair os dados do PDF, incluindo as medidas de demanda
def extrair_dados_do_pdf(caminho_do_pdf):
    dados = []
    
    with pdfplumber.open(caminho_do_pdf) as pdf:
        
        # Extrai os dados da segunda página do PDF, incluindo as medidas de demanda
        pagina1 = pdf.pages[1].extract_text().splitlines()
        for pagina in pagina1:
            tamanho = len(pagina.split())
            if tamanho == 11:
                arquivo = pagina.split(' ')
                arq = []
                arq.append(arquivo)

                for a in arq:
                    mes_ano = f'{mapear_meses(a[0])}/20{a[2]}'

                    try:
                        mes_ano_formatado = pd.to_datetime(mes_ano, format='%b/%Y')
                    except ValueError:
                        mes_ano_formatado = pd.to_datetime(mes_ano.replace('/', ' '), format='%b %Y', errors='coerce')

                    demanda_medida = {
                        'mes': mes_ano_formatado,
                        'ponta': float(a[3].replace(',', '.')),
                        'fora_ponta': float(a[4].replace(',', '.'))
                        #'reativo_excedente': float(a[5].replace(',', '.'))
                    }
                    dados.append(demanda_medida)

    df = pd.DataFrame(dados)
    return df

def mapear_dados_do_pdf(caminho_do_pdf):
    dados = []
    
    # Extrai os dados da primeira página do PDF
    with pdfplumber.open(caminho_do_pdf) as pdf:
        pagina0 = pdf.pages[0].extract_text().splitlines()
        for pag in pagina0:
            pagina = pag.splitlines()
            dados.append(pagina)
    return dados

# Função para processar o PDF, incluindo o cálculo da demanda final
def processar_pdf(caminho_do_pdf):
    
    df = extrair_dados_do_pdf(caminho_do_pdf)
    dados_2 = mapear_dados_do_pdf(caminho_do_pdf)

    lista_texto = []
    for dado in dados_2:
        for d in dado:
            lista_texto.append(d)

    dados_fornecimento = []
    for texto in lista_texto:
        if 'DEMANDA - kW' in texto:
            dados_fornecimento.append(texto.splitlines())  
    
    demanda  = dados_fornecimento[-1]
    demanda = demanda[0].split()[-1]
        
    return df, demanda


# Função para realizar a análise de energia
def analise_energia(df, caminho_do_pdf):
    VALOR_DA_DEMANDA = 28.107471
    MULTA = 56.214942

    df, demanda = processar_pdf(caminho_do_pdf)
    df = df.loc[(df['ponta'] > 0) & (df['fora_ponta'] > 0)]
    demanda = int(demanda)

    df['demanda_contratada'] = demanda #df['ponta'].max()  # Exemplo, considerando que a demanda contratada é o máximo valor de ponta
    df['demanda_mais_5'] = float(demanda)*(1+0.05)
    df['maior_demanda'] = df[['ponta', 'fora_ponta']].max(axis=1)
    df['demanda_faturada'] = np.where(df['maior_demanda'] >= df['demanda_mais_5'],
                                    (df['maior_demanda'] * VALOR_DA_DEMANDA) + ((df['maior_demanda'] - df['demanda_contratada']) * MULTA),
                                    df['demanda_contratada'] * VALOR_DA_DEMANDA)

    demanda_sugerida = df[['ponta', 'fora_ponta']].max(axis=1)
    demanda_sugerida = round(demanda_sugerida.max() * (1 - 0.05) + 1, 0)

    df['demanda_sugerida'] = demanda_sugerida
    df['valor_demanda_sug'] = df['demanda_sugerida'] * VALOR_DA_DEMANDA
    df['diferenca'] = df['valor_demanda_sug'] - df['demanda_faturada']

    media_anual = df['maior_demanda'].mean()
    maior_demanda = df['maior_demanda'].max()
    demanda_cont = (df['demanda_contratada'] * VALOR_DA_DEMANDA).sum()
    demanda_faturada = (df['demanda_faturada']).sum()
    vlr_demanda_sugerida = (df['valor_demanda_sug']).sum()
    diferenca = vlr_demanda_sugerida - demanda_faturada
    

    return df, media_anual, demanda_cont, demanda_faturada, vlr_demanda_sugerida, diferenca, demanda, maior_demanda,demanda_sugerida

# Função principal para executar o aplicativo Streamlit
def main():
    st.set_page_config(layout="wide")
    st.title(f"Análise de Energia")
    
    with st.sidebar:
        st.title('Analise Talão de Energia')
        st.subheader('Talão de energia aqui!')
        uploaded_file = st.sidebar.file_uploader("Selecione um talão PDF", type="pdf")
    
    df = pd.DataFrame()  

    if uploaded_file:
        try:
            df, media_anual, demanda_cont, demanda_faturada, vlr_demanda_sugerida, diferenca, demanda, maior_demanda,demanda_sugerida = analise_energia(df, uploaded_file)
            
            st.subheader(f'Analisando - {uploaded_file.name}')

            if isinstance(df, pd.DataFrame) and not df.empty:
                df, media_anual, demanda_cont, demanda_faturada, vlr_demanda_sugerida, diferenca, demanda, maior_demanda, demanda_sugerida = analise_energia(df, uploaded_file)
                
                col_main1, col_main2, col_main3, col_main4 = st.columns(4)

                with col_main1:
                    total_faturado_mes = 'R$ {:,.2f}'.format(demanda_cont)
                    st.metric('Valor Anual Demanda Contratada', total_faturado_mes)

                with col_main2:
                    soma_valores = 'R$ {:,.2f}'.format(demanda_faturada)
                    st.metric('Valor Anual Demanda Faturada', soma_valores)

                with col_main3:
                    soma_valores = 'R$ {:,.2f}'.format(vlr_demanda_sugerida)
                    st.metric('Valor Anual Demanda Sugerida', soma_valores)

                with col_main4:
                    reducao_fatura = 'R$ {:,.2f}'.format(diferenca)
                    st.metric('Projeção de Redução Anual', reducao_fatura, delta=round(((diferenca/demanda_faturada))*100, 2))

                
                valor_verde = 'Adotar a demanda sugerida.'
                valor_vermelho = 'Não adotar demanda sugerida, procurar outra alternartiva para redução dos custos de demanda.'
                
                if diferenca < 0:
                    st.write(f"<h4 style='color:green;'>{valor_verde}</h4>", unsafe_allow_html=True)
                else: 
                    st.write(f"<h4 style='color:red;'> {valor_vermelho}</h4>", unsafe_allow_html=True)
                    
                with st.container():
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric('Demanda Contratada', demanda)

                    with col2:
                        st.metric('Demanda Maior 12 Meses', maior_demanda, delta=round(((maior_demanda/demanda)-1)*100, 2))

                    with col3:
                        st.metric('Demanda Sugerida', demanda_sugerida, delta=round(((demanda_sugerida/demanda)-1)*100, 2))
                    
                    with col4:
                        st.metric('Demanda Média Anual', round(media_anual, 2), delta=round(((media_anual/demanda)-1)*100, 2))

        except Exception as e:
            st.warning(f"Erro ao processar o talão de energia: {str(e)}")

    if not df.empty:      
        cor_ponta = '#1f77b4'  # Azul
        cor_fora_ponta = '#ff7f0e'  # Laranja
        
        media_anual = df[['ponta', 'fora_ponta']].mean().mean()

        fig = go.Figure(data=[
            go.Bar(name='Ponta', x=df['mes'], y=df['ponta'], marker_color=cor_ponta, text=df['ponta'], textposition='outside'),
            go.Bar(name='Fora Ponta', x=df['mes'], y=df['fora_ponta'], marker_color=cor_fora_ponta, text=df['fora_ponta'], textposition='outside'),
            go.Scatter(x=df['mes'], y=[media_anual] * len(df), mode='lines', name='Demanda Média Anual', line=dict(color='red'))
        ])
        fig.update_layout(barmode='group')
        
        st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
