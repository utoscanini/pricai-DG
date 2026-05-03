import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

st.set_page_config(
    page_title='Buscador de Estudios Genéticos - PRICAI',
    page_icon='🧬',
    layout='wide'
)

st.markdown("""
    <style>
        .block-container { padding-top: 3rem; }
        h1 { color: #0d1b6e; font-family: 'Arial', sans-serif; font-size: 1.8rem; }
        h2, h3 { color: #0d1b6e; font-family: 'Arial', sans-serif; }
        hr { border: 1px solid #cc0000; margin-bottom: 1rem; }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def cargar_datos():
    df = pd.read_csv('Listado-tab.txt', sep='\t')
    df.columns = df.columns.str.strip()
    df = df.fillna('')
    return df

df = cargar_datos()

def generar_pdf(titulo, subtitulo, dataframe):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists('logo.png'):
        pdf.image('logo.png', x=10, y=10, w=60)
    pdf.set_y(40)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(13, 27, 110)
    pdf.cell(0, 10, titulo, ln=True, align='C')
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, subtitulo, ln=True, align='C')
    pdf.ln(5)
    pdf.set_draw_color(204, 0, 0)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    cols = list(dataframe.columns)
    n = len(cols)
    if n == 3:
        col_widths = [12, 98, 80]
    elif n == 5:
        col_widths = [12, 30, 60, 60, 28]
    else:
        col_widths = [190 // n] * n
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(255, 255, 255)
    pdf.set_fill_color(13, 27, 110)
    for i, col in enumerate(cols):
        pdf.cell(col_widths[i], 8, col, border=1, fill=True)
    pdf.ln()
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(0, 0, 0)
    fill = False
    for _, row in dataframe.iterrows():
        if fill:
            pdf.set_fill_color(230, 235, 255)
        else:
            pdf.set_fill_color(255, 255, 255)
        y_start = pdf.get_y()
        x_start = 10
        cell_texts = [str(row[col]) for col in cols]
        max_height = 6
        for i, text in enumerate(cell_texts):
            lines = pdf.multi_cell(col_widths[i], 6, text, border=0, align='L', split_only=True)
            max_height = max(max_height, len(lines) * 6)
        x = x_start
        for i, text in enumerate(cell_texts):
            pdf.set_xy(x, y_start)
            pdf.multi_cell(col_widths[i], 6, text, border=1, align='L', fill=fill)
            x += col_widths[i]
        pdf.set_xy(x_start, y_start + max_height)
        fill = not fill
    pdf.ln(10)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(130, 130, 130)
    pdf.cell(0, 6, 'PRICAI - Primer Centro Argentino de Inmunogenética', align='C')
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as f:
        pdf.output(f.name)
        return f.name

def enviar_mail(nombre, email, telefono, mensaje, adjunto, resultado_texto):
    gmail_user = st.secrets["GMAIL_USER"]
    gmail_password = st.secrets["GMAIL_PASSWORD"]
    destinatario = "info@pricai.com.ar"

    msg = MIMEMultipart()
    msg['From'] = gmail_user
    msg['To'] = destinatario
    msg['Subject'] = f'Solicitud de información / presupuesto - {nombre}'

    cuerpo = f"""
Solicitud de información / presupuesto

Nombre: {nombre}
Email: {email}
Teléfono: {telefono}
Mensaje: {mensaje}

{resultado_texto}
"""
    msg.attach(MIMEText(cuerpo, 'plain'))

    if adjunto is not None:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(adjunto.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{adjunto.name}"')
        msg.attach(part)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, destinatario, msg.as_string())

st.markdown('<br>', unsafe_allow_html=True)
col1, col2 = st.columns([1, 3])
with col1:
    st.image('logo.png', width=220)
with col2:
    st.title('Buscador de Estudios Genéticos')
    st.markdown('**Diagnóstico Genético Molecular**')

st.markdown('<hr>', unsafe_allow_html=True)

tipo_busqueda = st.radio(
    'Seleccioná el tipo de búsqueda:',
    ['Por Especialidad / Patología', 'Por Gen']
)

st.markdown('---')

resultado_para_mail = ""
resultado = None

if tipo_busqueda == 'Por Especialidad / Patología':
    especialidades = sorted(df['Especialidad'].unique())
    especialidad = st.selectbox('Especialidad:', especialidades)
    patologias = sorted(df[df['Especialidad'] == especialidad]['Patología'].unique())
    patologia = st.selectbox('Patología:', patologias)
    resultado = df[(df['Especialidad'] == especialidad) & (df['Patología'] == patologia)][['Genes', 'Metodología']].reset_index(drop=True)
    resultado.index += 1
    if not resultado.empty:
        st.subheader('Genes y Metodologías asociadas:')
        st.dataframe(resultado, column_config={
            'Genes': st.column_config.TextColumn('Genes', width='large'),
            'Metodología': st.column_config.TextColumn('Metodología', width='medium'),
        }, use_container_width=True)
        resultado_para_mail = f"Búsqueda: {especialidad} / {patologia}\n\n{resultado.to_string()}"
        if st.button('📄 Descargar PDF'):
            pdf_df = resultado.copy().reset_index()
            pdf_df.columns = ['N°', 'Genes', 'Metodología']
            pdf_path = generar_pdf('Estudios Genéticos', patologia, pdf_df)
            with open(pdf_path, 'rb') as f:
                st.download_button(label='⬇️ Hacer clic para descargar', data=f,
                    file_name=f'PRICAI_{patologia[:30]}.pdf', mime='application/pdf')

else:
    gen_busqueda = st.text_input('Ingresá el nombre del gen:')
    if gen_busqueda:
        mascara = df['Genes'].str.contains(gen_busqueda, case=False, na=False)
        resultado = df[mascara][['Especialidad', 'Patología', 'Genes', 'Metodología']].copy()
        def genes_coincidentes(celda):
            genes = [g.strip() for g in celda.split(',')]
            coincidencias = [g for g in genes if gen_busqueda.lower() in g.lower()]
            return ', '.join(coincidencias)
        resultado['Gen encontrado'] = resultado['Genes'].apply(genes_coincidentes)
        resultado = resultado[['Gen encontrado', 'Especialidad', 'Patología', 'Metodología']].reset_index(drop=True)
        resultado.index += 1
        if not resultado.empty:
            st.subheader(f'Resultados para "{gen_busqueda}":')
            st.dataframe(resultado, column_config={
                'Gen encontrado': st.column_config.TextColumn('Gen encontrado', width='small'),
                'Especialidad': st.column_config.TextColumn('Especialidad', width='medium'),
                'Patología': st.column_config.TextColumn('Patología', width='large'),
                'Metodología': st.column_config.TextColumn('Metodología', width='medium'),
            }, use_container_width=True)
            resultado_para_mail = f"Búsqueda por gen: {gen_busqueda}\n\n{resultado.to_string()}"
            if st.button('📄 Descargar PDF'):
                pdf_df = resultado.copy().reset_index()
                pdf_df.columns = ['N°', 'Gen encontrado', 'Especialidad', 'Patología', 'Metodología']
                pdf_path = generar_pdf(f'Estudios Genéticos - Gen: {gen_busqueda}', 'Resultados de búsqueda', pdf_df)
                with open(pdf_path, 'rb') as f:
                    st.download_button(label='⬇️ Hacer clic para descargar', data=f,
                        file_name=f'PRICAI_gen_{gen_busqueda}.pdf', mime='application/pdf')
        else:
            st.warning('No se encontraron resultados.')

st.markdown('---')
st.subheader('📧 Solicitar información / presupuesto')

with st.form('formulario_mail'):
    nombre = st.text_input('Nombre completo *')
    email = st.text_input('Email de contacto *')
    telefono = st.text_input('Teléfono celular *')
    mensaje = st.text_area('Mensaje (opcional)')
    adjunto = st.file_uploader('Orden médica * (PDF o imagen)', type=['pdf', 'png', 'jpg', 'jpeg'])
    enviar = st.form_submit_button('📨 Enviar solicitud')

    if enviar:
        if not nombre or not email or not telefono:
            st.error('Por favor completá los campos obligatorios: nombre, email y teléfono.')
        elif adjunto is None:
            st.error('Por favor adjuntá la orden médica.')
        else:
            try:
                enviar_mail(nombre, email, telefono, mensaje, adjunto, resultado_para_mail)
                st.success('¡Solicitud enviada correctamente! Nos comunicaremos a la brevedad.')
            except Exception as e:
                st.error(f'Error al enviar el mail: {e}')

st.markdown('<hr>', unsafe_allow_html=True)
st.markdown('<p style="color: #888888; font-size: 0.8rem; text-align: center;">PRICAI - Primer Centro Argentino de Inmunogenética</p>', unsafe_allow_html=True)
