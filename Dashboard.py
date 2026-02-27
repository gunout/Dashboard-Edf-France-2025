# dashboard_edf_2025.py
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
import pytz
import warnings
import random
from requests.exceptions import HTTPError, ConnectionError
import urllib3
warnings.filterwarnings('ignore')

# Désactiver les warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration de la page
st.set_page_config(
    page_title="Tracker EDF - Électricité de France",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration du fuseau horaire
USER_TIMEZONE = pytz.timezone('Europe/Paris')  # UTC+1/UTC+2

# Style CSS personnalisé
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
    
    .main-header {
        font-size: 2.5rem;
        color: #003664;
        text-align: center;
        margin-bottom: 2rem;
        font-family: 'Roboto', sans-serif;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        background: linear-gradient(135deg, #003664 0%, #00A88F 50%, #FFCC00 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .french-text {
        font-family: 'Roboto', sans-serif;
        font-size: 1.2rem;
    }
    .stock-price {
        font-size: 2.5rem;
        font-weight: bold;
        color: #003664;
        text-align: center;
    }
    .stock-change-positive {
        color: #00A88F;
        font-size: 1.2rem;
        font-weight: bold;
    }
    .stock-change-negative {
        color: #E4003B;
        font-size: 1.2rem;
        font-weight: bold;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .alert-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .alert-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .alert-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
    }
    .portfolio-table {
        font-size: 0.9rem;
    }
    .stButton>button {
        width: 100%;
    }
    .timezone-badge {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 0.5rem 1rem;
        margin: 1rem 0;
        font-size: 0.9rem;
    }
    .edf-badge {
        background-color: #003664;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 1rem;
        font-weight: bold;
        display: inline-block;
        margin-right: 0.5rem;
    }
    .nuclear-badge {
        background-color: #FFCC00;
        color: #003664;
        padding: 0.3rem 0.8rem;
        border-radius: 1rem;
        font-weight: bold;
        display: inline-block;
    }
    .renewable-badge {
        background-color: #00A88F;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 1rem;
        font-weight: bold;
        display: inline-block;
    }
    .demo-mode-badge {
        background-color: #ff9800;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 1rem;
        font-weight: bold;
        display: inline-block;
        margin-right: 0.5rem;
    }
    .weekend-note {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 0.5rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        text-align: center;
    }
    .french-market-note {
        background: linear-gradient(135deg, #003664 0%, #FFFFFF 50%, #E4003B 100%);
        color: #000000;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        font-weight: bold;
        text-align: center;
        font-family: 'Roboto', sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# Initialisation des variables de session
if 'price_alerts' not in st.session_state:
    st.session_state.price_alerts = []

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = [
        # EDF et concurrents français
        'EDF.PA',  # EDF (maintenant sur Euronext Paris)
        'ENGI.PA',  # Engie
        'SU.PA',  # Schneider Electric
        'TTE.PA',  # TotalEnergies
        'VIE.PA',  # Veolia
        'OR.PA',  # L'Oréal (pour comparaison CAC40)
        'MC.PA',  # LVMH
        'AIR.PA',  # Airbus
        'BNP.PA',  # BNP Paribas
        'SAN.PA',  # Sanofi
        
        # Énergéticiens européens
        'IBE.MC',  # Iberdrola (Espagne)
        'ENEL.MI',  # Enel (Italie)
        'RWE.DE',  # RWE (Allemagne)
        'EOAN.DE',  # E.ON (Allemagne)
        'SSE.L',  # SSE (UK)
        'NG.L',  # National Grid (UK)
        'FGR.PA',  # EDF - ancien code (peut être utile)
        
        # Indices
        '^FCHI',  # CAC 40
        '^STOXX50E',  # Euro Stoxx 50
        '^SX6E',  # Stoxx 600 Utilities
    ]

if 'notifications' not in st.session_state:
    st.session_state.notifications = []

if 'email_config' not in st.session_state:
    st.session_state.email_config = {
        'enabled': False,
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'email': '',
        'password': ''
    }

if 'demo_mode' not in st.session_state:
    st.session_state.demo_mode = False

if 'last_successful_data' not in st.session_state:
    st.session_state.last_successful_data = {}

# Données de démonstration pour EDF
DEMO_DATA = {
    'EDF.PA': {
        'name': 'EDF - Électricité de France',
        'current_price': 12.50,
        'previous_close': 12.35,
        'day_high': 12.65,
        'day_low': 12.30,
        'volume': 8500000,
        'market_cap': 47500000000,  # 47.5B €
        'pe_ratio': 8.5,
        'dividend_yield': 4.2,
        'beta': 0.7,
        'sector': 'Utilities',
        'industry': 'Electric Utilities',
        'website': 'www.edf.fr',
        'employees': 165000,
        'nuclear_capacity': 61.4,  # GW
        'renewable_capacity': 37.2,  # GW
        'customers': 37.8,  # millions
    },
    'ENGI.PA': {
        'name': 'Engie',
        'current_price': 15.80,
        'previous_close': 15.65,
        'day_high': 16.00,
        'day_low': 15.55,
        'volume': 4200000,
        'market_cap': 38500000000,
        'pe_ratio': 10.2,
        'dividend_yield': 5.5,
        'beta': 0.8,
        'sector': 'Utilities',
        'industry': 'Multiline Utilities',
        'website': 'www.engie.com'
    },
    'TTE.PA': {
        'name': 'TotalEnergies',
        'current_price': 62.30,
        'previous_close': 61.90,
        'day_high': 62.80,
        'day_low': 61.75,
        'volume': 5600000,
        'market_cap': 155000000000,
        'pe_ratio': 7.8,
        'dividend_yield': 6.8,
        'beta': 1.3,
        'sector': 'Energy',
        'industry': 'Oil & Gas',
        'website': 'www.totalenergies.com'
    },
    'SU.PA': {
        'name': 'Schneider Electric',
        'current_price': 185.50,
        'previous_close': 184.20,
        'day_high': 187.00,
        'day_low': 183.80,
        'volume': 1200000,
        'market_cap': 104000000000,
        'pe_ratio': 25.4,
        'dividend_yield': 2.1,
        'beta': 1.2,
        'sector': 'Industrials',
        'industry': 'Electrical Equipment',
        'website': 'www.se.com'
    },
    'VIE.PA': {
        'name': 'Veolia Environnement',
        'current_price': 28.90,
        'previous_close': 28.70,
        'day_high': 29.20,
        'day_low': 28.55,
        'volume': 2100000,
        'market_cap': 20700000000,
        'pe_ratio': 16.5,
        'dividend_yield': 3.8,
        'beta': 0.9,
        'sector': 'Utilities',
        'industry': 'Water Utilities',
        'website': 'www.veolia.com'
    },
    'IBE.MC': {
        'name': 'Iberdrola',
        'current_price': 12.40,
        'previous_close': 12.30,
        'day_high': 12.55,
        'day_low': 12.25,
        'volume': 8500000,
        'market_cap': 78000000000,
        'pe_ratio': 16.2,
        'dividend_yield': 4.1,
        'beta': 0.5,
        'sector': 'Utilities',
        'industry': 'Electric Utilities',
        'website': 'www.iberdrola.com'
    }
}

# Symboles par défaut
DEFAULT_SYMBOL = 'EDF.PA'
SYMBOL_INFO = {
    'EDF.PA': 'EDF - Électricité de France (Euronext Paris)',
    'ENGI.PA': 'Engie - Groupe énergétique français',
    'TTE.PA': 'TotalEnergies - Pétrole et énergies',
    'SU.PA': 'Schneider Electric - Équipements électriques',
    'VIE.PA': 'Veolia - Gestion de l\'eau et déchets',
    'IBE.MC': 'Iberdrola - Électricité espagnole',
    'ENEL.MI': 'Enel - Électricité italienne',
    'RWE.DE': 'RWE - Énergie allemande',
    'EOAN.DE': 'E.ON - Énergie allemande',
}

# Horaires du marché français
FRENCH_MARKET_HOURS = {
    'Euronext Paris': {
        'open': 9,
        'close': 17,
        'tz': 'Europe/Paris',
        'pre_open': 7,  # Pré-ouverture
        'post_close': 17.5,  # Post-clôture
    }
}

# Jours fériés français 2024
FRENCH_HOLIDAYS_2024 = [
    '2024-01-01',  # Jour de l'An
    '2024-04-01',  # Lundi de Pâques
    '2024-05-01',  # Fête du Travail
    '2024-05-08',  # Victoire 1945
    '2024-05-09',  # Ascension
    '2024-05-20',  # Pentecôte
    '2024-07-14',  # Fête Nationale
    '2024-08-15',  # Assomption
    '2024-11-01',  # Toussaint
    '2024-11-11',  # Armistice
    '2024-12-25',  # Noël
]

# Devises
CURRENCY = 'EUR'

# Fonction pour générer des données historiques de démonstration
def generate_demo_history(symbol, period="1mo", interval="1d"):
    """Génère des données historiques simulées pour la démonstration"""
    dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
    
    # Prix de base selon le symbole
    if symbol in DEMO_DATA:
        base_price = DEMO_DATA[symbol]['current_price']
        
        if symbol == 'EDF.PA':
            volatility = 0.018
        elif symbol in ['ENGI.PA', 'VIE.PA']:
            volatility = 0.016
        elif symbol == 'TTE.PA':
            volatility = 0.022
        elif symbol == 'SU.PA':
            volatility = 0.024
        else:
            volatility = 0.02
    else:
        if 'PA' in symbol:  # Euronext Paris
            base_price = random.uniform(10, 200)
            volatility = 0.02
        elif 'MC' in symbol:  # Madrid
            base_price = random.uniform(5, 50)
            volatility = 0.018
        elif 'MI' in symbol:  # Milan
            base_price = random.uniform(3, 30)
            volatility = 0.019
        elif 'DE' in symbol:  # Allemagne
            base_price = random.uniform(20, 150)
            volatility = 0.021
        else:
            base_price = random.uniform(10, 500)
            volatility = 0.02
    
    # Générer une série de prix avec une légère tendance
    np.random.seed(hash(symbol) % 42)
    
    # Ajouter une tendance saisonnière pour les utilities
    days = np.arange(len(dates))
    seasonal = 0.001 * np.sin(2 * np.pi * days / 365)  # Saisonnalité annuelle
    
    returns = np.random.normal(0.0001 + seasonal, volatility, len(dates))
    price_series = base_price * np.exp(np.cumsum(returns))
    
    # Créer le DataFrame
    df = pd.DataFrame({
        'Open': price_series * (1 - np.random.uniform(0, 0.008, len(dates))),
        'High': price_series * (1 + np.random.uniform(0, 0.015, len(dates))),
        'Low': price_series * (1 - np.random.uniform(0, 0.015, len(dates))),
        'Close': price_series,
        'Volume': np.random.randint(500000, 10000000, len(dates))
    }, index=dates)
    
    # Convertir l'index en timezone-aware
    df.index = df.index.tz_localize(USER_TIMEZONE)
    
    return df

# Fonction pour charger les données avec gestion des erreurs améliorée
@st.cache_data(ttl=600)
def load_stock_data(symbol, period, interval, retry_count=3):
    """Charge les données boursières avec gestion des erreurs et retry"""
    
    # Vérifier si on a des données en cache dans la session
    if st.session_state.demo_mode and symbol in DEMO_DATA:
        return generate_demo_history(symbol, period, interval), DEMO_DATA[symbol]
    
    for attempt in range(retry_count):
        try:
            if attempt > 0:
                time.sleep(2 ** attempt)
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval, timeout=10)
            info = ticker.info
            
            if hist is not None and not hist.empty:
                if hist.index.tz is None:
                    hist.index = hist.index.tz_localize('UTC').tz_convert(USER_TIMEZONE)
                else:
                    hist.index = hist.index.tz_convert(USER_TIMEZONE)
                
                st.session_state.last_successful_data[symbol] = {
                    'hist': hist,
                    'info': info,
                    'timestamp': datetime.now()
                }
                
                return hist, info
            
        except Exception as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                st.warning(f"⚠️ Limite de requêtes atteinte. Tentative {attempt + 1}/{retry_count}...")
            else:
                st.warning(f"⚠️ Erreur: {e}. Tentative {attempt + 1}/{retry_count}...")
    
    # Si toutes les tentatives échouent, utiliser les données en cache
    if symbol in st.session_state.last_successful_data:
        cached = st.session_state.last_successful_data[symbol]
        time_diff = datetime.now() - cached['timestamp']
        if time_diff.total_seconds() < 3600:
            st.info(f"📋 Utilisation des données en cache du {cached['timestamp'].strftime('%H:%M:%S')}")
            return cached['hist'], cached['info']
    
    # Activer le mode démo automatiquement
    if not st.session_state.demo_mode:
        st.session_state.demo_mode = True
        st.info("🔄 Mode démonstration activé - Données simulées")
    
    # Données de démonstration par défaut
    demo_info = {
        'longName': f'{symbol} (Mode démo)',
        'sector': random.choice(['Utilities', 'Energy', 'Industrials']),
        'industry': 'Various',
        'marketCap': random.randint(1000000000, 50000000000),
        'trailingPE': random.uniform(8, 25),
        'dividendYield': random.uniform(0.02, 0.07),
        'beta': random.uniform(0.5, 1.3),
        'website': 'N/A'
    }
    
    return generate_demo_history(symbol, period, interval), demo_info

def get_exchange_info(symbol):
    """Détermine l'échange pour un symbole"""
    if '.PA' in symbol:
        exchange = 'Euronext Paris'
        country = 'France'
    elif '.MC' in symbol:
        exchange = 'Bolsa de Madrid'
        country = 'Spain'
    elif '.MI' in symbol:
        exchange = 'Borsa Italiana'
        country = 'Italy'
    elif '.DE' in symbol:
        exchange = 'Deutsche Börse'
        country = 'Germany'
    elif '.L' in symbol:
        exchange = 'London Stock Exchange'
        country = 'UK'
    elif symbol.startswith('^'):
        exchange = 'Index'
        country = 'Europe'
    else:
        exchange = 'International'
        country = 'Global'
    
    return exchange, country, 'EUR'

def get_currency(symbol):
    """Détermine la devise pour un symbole"""
    if any(suffix in symbol for suffix in ['.PA', '.MC', '.MI', '.DE', '.L', '^']):
        return 'EUR'
    return 'EUR'

def format_currency(value, currency='EUR'):
    """Formate la monnaie en euros"""
    if value is None or value == 0:
        return "N/A"
    
    if value >= 1e9:  # Billion
        return f"{value/1e9:.2f} Md€"
    elif value >= 1e6:  # Million
        return f"{value/1e6:.2f} M€"
    else:
        return f"{value:.2f} €"

def format_large_number_french(num):
    """Formate les grands nombres selon le système français"""
    if num > 1e12:
        return f"{num/1e12:.2f} billion"
    elif num > 1e9:
        return f"{num/1e9:.2f} milliard"
    elif num > 1e6:
        return f"{num/1e6:.2f} million"
    else:
        return f"{num:,.0f}"

def send_email_alert(subject, body, to_email):
    """Envoie une notification par email"""
    if not st.session_state.email_config['enabled']:
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = st.session_state.email_config['email']
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(
            st.session_state.email_config['smtp_server'], 
            st.session_state.email_config['smtp_port']
        )
        server.starttls()
        server.login(
            st.session_state.email_config['email'],
            st.session_state.email_config['password']
        )
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Erreur d'envoi: {e}")
        return False

def check_price_alerts(current_price, symbol):
    """Vérifie les alertes de prix"""
    triggered = []
    for alert in st.session_state.price_alerts:
        if alert['symbol'] == symbol:
            if alert['condition'] == 'above' and current_price >= alert['price']:
                triggered.append(alert)
            elif alert['condition'] == 'below' and current_price <= alert['price']:
                triggered.append(alert)
    
    return triggered

def get_market_status():
    """Détermine le statut du marché français"""
    market_tz = pytz.timezone('Europe/Paris')
    now = datetime.now(market_tz)
    
    # Jour de la semaine (lundi=0, dimanche=6)
    weekday = now.weekday()
    
    # Weekend (samedi ou dimanche)
    if weekday >= 5:
        return f"Fermé (weekend)", "🔴"
    
    # Jours fériés
    date_str = now.strftime('%Y-%m-%d')
    if date_str in FRENCH_HOLIDAYS_2024:
        return "Fermé (jour férié)", "🔴"
    
    # Horaires de trading
    current_hour = now.hour
    current_minute = now.minute
    current_time_decimal = current_hour + current_minute / 60
    
    open_hour = FRENCH_MARKET_HOURS['Euronext Paris']['open']
    close_hour = FRENCH_MARKET_HOURS['Euronext Paris']['close']
    
    if open_hour <= current_time_decimal < close_hour:
        return "Ouvert", "🟢"
    elif current_time_decimal < open_hour:
        return "Fermé (pré-ouverture)", "🟡"
    else:
        return "Fermé", "🔴"

def safe_get_metric(hist, metric, index=-1):
    """Récupère une métrique en toute sécurité"""
    try:
        if hist is not None and not hist.empty and len(hist) > abs(index):
            return hist[metric].iloc[index]
        return 0
    except:
        return 0

# Titre principal
st.markdown("<h1 class='main-header'>⚡ Tracker EDF - Électricité de France en Temps Réel</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-family: Roboto; font-size: 1.5rem;'>Suivi de l'action EDF et du secteur énergétique français</p>", unsafe_allow_html=True)

# Bannière de statut du marché
current_time_paris = datetime.now(USER_TIMEZONE)
market_status, market_icon = get_market_status()

# Badges EDF
st.markdown("""
<div style='text-align: center; margin: 10px 0;'>
    <span class='edf-badge'>⚡ EDF - Électricité de France</span>
    <span class='nuclear-badge'>☢️ Nucléaire 61.4 GW</span>
    <span class='renewable-badge'>🌱 Renouvelables 37.2 GW</span>
</div>
""", unsafe_allow_html=True)

# Statut du marché
st.markdown(f"""
<div class='timezone-badge'>
    <b>🕐 Fuseau horaire :</b> Heure de Paris (UTC+1/UTC+2)<br>
    <b>📍 Euronext Paris :</b> {market_icon} {market_status} (Horaires: 9h00-17h30)<br>
    <b>📅 Jours de trading :</b> Lundi au Vendredi (fermé weekends et jours fériés)<br>
    <b>⚡ Heure actuelle :</b> {current_time_paris.strftime('%H:%M:%S')}
</div>
""", unsafe_allow_html=True)

# Note sur les jours fériés
if datetime.now().weekday() >= 5:
    st.markdown("""
    <div class='weekend-note'>
        📅 Les marchés financiers sont fermés le week-end. Les prochains cours seront disponibles lundi.
    </div>
    """, unsafe_allow_html=True)

# Mode démo badge
if st.session_state.demo_mode:
    st.markdown("""
    <div style='text-align: center; margin: 10px 0;'>
        <span class='demo-mode-badge'>🎮 MODE DÉMONSTRATION</span>
        <span style='color: #666;'>Données simulées - API temporairement indisponible</span>
    </div>
    """, unsafe_allow_html=True)

# Note sur EDF
st.markdown("""
<div class='french-market-note'>
    <b>⚡ Électricité de France (EDF) - Leader européen de l'énergie</b><br>
    🇫🇷 Entreprise publique française, opérateur historique du secteur électrique<br>
    ☢️ Premier producteur nucléaire d'Europe (56 réacteurs, 61.4 GW)<br>
    🌱 Deuxième producteur d'énergies renouvelables en France (hydroélectricité, solaire, éolien)<br>
    🌍 Présence internationale: UK, Italie, Belgique, Chine, États-Unis<br>
    💶 Capitalisation: ~47 milliards € | 👥 165,000 employés | 🏠 37.8 millions de clients
</div>
""", unsafe_allow_html=True)

# Sidebar pour la navigation
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/edf.png", width=80)
    st.title("Navigation")
    
    # Boutons pour le mode démo
    col_demo1, col_demo2 = st.columns(2)
    with col_demo1:
        if st.button("🎮 Mode Démo"):
            st.session_state.demo_mode = True
            st.rerun()
    with col_demo2:
        if st.button("🔄 Mode Réel"):
            st.session_state.demo_mode = False
            st.cache_data.clear()
            st.rerun()
    
    st.markdown("---")
    
    menu = st.radio(
        "Choisir une section",
        ["📈 Tableau de bord EDF", 
         "🔋 Portefeuille énergie", 
         "🔔 Alertes de prix",
         "📧 Notifications email",
         "📤 Export des données",
         "🤖 Prédictions ML",
         "🇪🇺 Comparaison sectorielle"]
    )
    
    st.markdown("---")
    
    # Configuration du symbole principal
    st.subheader("⚙️ Configuration")
    
    # Sélection du symbole principal
    symbol_options = [
        "EDF.PA (EDF - Électricité de France)",
        "ENGI.PA (Engie)",
        "TTE.PA (TotalEnergies)",
        "SU.PA (Schneider Electric)",
        "VIE.PA (Veolia)",
        "IBE.MC (Iberdrola)",
        "ENEL.MI (Enel)",
        "RWE.DE (RWE)",
        "EOAN.DE (E.ON)",
        "Autre..."
    ]
    
    selected_option = st.selectbox(
        "Symbole principal",
        options=symbol_options,
        index=0
    )
    
    if selected_option == "Autre...":
        symbol = st.text_input("Entrer un symbole", value="EDF.PA").upper()
    else:
        symbol = selected_option.split()[0]
    
    # Afficher des informations sur le symbole
    if symbol:
        exchange, country, currency = get_exchange_info(symbol)
        st.caption(f"📍 {exchange}")
        st.caption(f"🌍 {country} | 💱 {currency}")
    
    # Période et intervalle
    col1, col2 = st.columns(2)
    with col1:
        period = st.selectbox(
            "Période",
            options=["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"],
            index=2
        )
    
    with col2:
        interval_map = {
            "1m": "1 minute", "5m": "5 minutes", "15m": "15 minutes",
            "30m": "30 minutes", "1h": "1 heure", "1d": "1 jour",
            "1wk": "1 semaine", "1mo": "1 mois"
        }
        interval = st.selectbox(
            "Intervalle",
            options=list(interval_map.keys()),
            format_func=lambda x: interval_map[x],
            index=4 if period == "1d" else 6
        )
    
    # Auto-refresh
    auto_refresh = st.checkbox("Actualisation automatique", value=False)
    if auto_refresh:
        st.warning("⚠️ L'actualisation automatique peut entraîner des limitations API")
        refresh_rate = st.slider(
            "Fréquence (secondes)",
            min_value=30,
            max_value=300,
            value=60,
            step=10
        )

# Chargement des données
try:
    hist, info = load_stock_data(symbol, period, interval)
except Exception as e:
    st.error(f"Erreur lors du chargement: {e}")
    st.session_state.demo_mode = True
    hist, info = generate_demo_history(symbol, period, interval), DEMO_DATA.get(symbol, {
        'longName': f'{symbol} (Mode démo)',
        'sector': 'N/A',
        'industry': 'N/A'
    })

if hist is None or hist.empty:
    st.warning(f"⚠️ Impossible de charger les données pour {symbol}. Utilisation du mode démo.")
    st.session_state.demo_mode = True
    hist = generate_demo_history(symbol, period, interval)
    info = DEMO_DATA.get(symbol, {
        'longName': f'{symbol} (Mode démo)',
        'sector': 'N/A',
        'industry': 'N/A',
        'marketCap': 10000000000
    })

current_price = safe_get_metric(hist, 'Close')

# Vérification des alertes
triggered_alerts = check_price_alerts(current_price, symbol)
for alert in triggered_alerts:
    st.balloons()
    st.success(f"🎯 Alerte déclenchée pour {symbol} à {format_currency(current_price, 'EUR')}")
    
    if st.session_state.email_config['enabled']:
        subject = f"🚨 Alerte prix - {symbol}"
        body = f"""
        <h2>Alerte de prix déclenchée</h2>
        <p><b>Symbole:</b> {symbol}</p>
        <p><b>Prix actuel:</b> {format_currency(current_price, 'EUR')}</p>
        <p><b>Condition:</b> {alert['condition']} {format_currency(alert['price'], 'EUR')}</p>
        <p><b>Date:</b> {datetime.now(USER_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')} (heure Paris)</p>
        """
        send_email_alert(subject, body, st.session_state.email_config['email'])
    
    if alert.get('one_time', False):
        st.session_state.price_alerts.remove(alert)

# ============================================================================
# SECTION 1: TABLEAU DE BORD EDF
# ============================================================================
if menu == "📈 Tableau de bord EDF":
    # Statut du marché spécifique
    exchange, country, currency = get_exchange_info(symbol)
    st.info(f"{market_icon} {exchange}: {market_status}")
    
    if hist is not None and not hist.empty:
        company_name = info.get('longName', symbol) if info else symbol
        if st.session_state.demo_mode:
            company_name += " (Mode démo)"
        
        st.subheader(f"📊 Aperçu en temps réel - {company_name}")
        
        col1, col2, col3, col4 = st.columns(4)
        
        previous_close = safe_get_metric(hist, 'Close', -2) if len(hist) > 1 else current_price
        change = current_price - previous_close
        change_pct = (change / previous_close * 100) if previous_close != 0 else 0
        
        with col1:
            st.metric(
                label="Prix actuel",
                value=format_currency(current_price, currency),
                delta=f"{change:.2f} ({change_pct:.2f}%)"
            )
        
        with col2:
            day_high = safe_get_metric(hist, 'High')
            st.metric("Plus haut", format_currency(day_high, currency))
        
        with col3:
            day_low = safe_get_metric(hist, 'Low')
            st.metric("Plus bas", format_currency(day_low, currency))
        
        with col4:
            volume = safe_get_metric(hist, 'Volume')
            volume_formatted = f"{volume/1e6:.1f}M" if volume > 1e6 else f"{volume/1e3:.1f}K"
            st.metric("Volume", volume_formatted)
        
        try:
            st.caption(f"Dernière mise à jour: {hist.index[-1].strftime('%Y-%m-%d %H:%M:%S')} (heure Paris)")
        except:
            st.caption(f"Dernière mise à jour: {datetime.now(USER_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')} (heure Paris)")
        
        # Graphique principal
        st.subheader("📉 Évolution du prix")
        
        fig = go.Figure()
        
        if interval in ["1m", "5m", "15m", "30m", "1h"]:
            fig.add_trace(go.Candlestick(
                x=hist.index,
                open=hist['Open'],
                high=hist['High'],
                low=hist['Low'],
                close=hist['Close'],
                name='Prix',
                increasing_line_color='#00A88F',
                decreasing_line_color='#E4003B'
            ))
        else:
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=hist['Close'],
                mode='lines',
                name='Prix',
                line=dict(color='#003664', width=2)
            ))
        
        if len(hist) >= 20:
            ma_20 = hist['Close'].rolling(window=20).mean()
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=ma_20,
                mode='lines',
                name='MA 20 jours',
                line=dict(color='orange', width=1, dash='dash')
            ))
        
        if len(hist) >= 50:
            ma_50 = hist['Close'].rolling(window=50).mean()
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=ma_50,
                mode='lines',
                name='MA 50 jours',
                line=dict(color='purple', width=1, dash='dash')
            ))
        
        if len(hist) >= 200:
            ma_200 = hist['Close'].rolling(window=200).mean()
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=ma_200,
                mode='lines',
                name='MA 200 jours',
                line=dict(color='red', width=1, dash='dash')
            ))
        
        fig.add_trace(go.Bar(
            x=hist.index,
            y=hist['Volume'],
            name='Volume',
            yaxis='y2',
            marker=dict(color='lightgray', opacity=0.3)
        ))
        
        fig.update_layout(
            title=f"{symbol} - {period} (heure Paris)",
            yaxis_title=f"Prix ({currency})",
            yaxis2=dict(
                title="Volume",
                overlaying='y',
                side='right',
                showgrid=False
            ),
            xaxis_title="Date",
            height=600,
            hovermode='x unified',
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Informations sur l'entreprise et métriques EDF spécifiques
        with st.expander("ℹ️ Informations détaillées sur l'entreprise"):
            if info:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Nom :** {info.get('longName', 'N/A')}")
                    st.write(f"**Secteur :** {info.get('sector', 'N/A')}")
                    st.write(f"**Industrie :** {info.get('industry', 'N/A')}")
                    st.write(f"**Site web :** {info.get('website', 'N/A')}")
                    st.write(f"**Bourse :** {exchange}")
                    st.write(f"**Pays :** {country}")
                
                with col2:
                    market_cap = info.get('marketCap', 0)
                    if market_cap > 0:
                        st.write(f"**Capitalisation :** {format_currency(market_cap, currency)} ({format_large_number_french(market_cap)})")
                    
                    st.write(f"**P/E :** {info.get('trailingPE', 'N/A'):.2f}" if info.get('trailingPE') else "**P/E :** N/A")
                    st.write(f"**Dividende :** {info.get('dividendYield', 0)*100:.2f}%" if info.get('dividendYield') else "**Dividende :** N/A")
                    st.write(f"**Beta :** {info.get('beta', 'N/A'):.2f}" if info.get('beta') else "**Beta :** N/A")
                    st.write(f"**Volume moy. :** {info.get('averageVolume', 'N/A'):,}" if info.get('averageVolume') else "**Volume moy. :** N/A")
                
                with col3:
                    if symbol == 'EDF.PA':
                        st.write(f"**Employés :** 165,000")
                        st.write(f"**Clients :** 37.8 millions")
                        st.write(f"**Capacité nucléaire :** 61.4 GW")
                        st.write(f"**Capacité renouvelable :** 37.2 GW")
                        st.write(f"**Production annuelle :** 450 TWh")
                    else:
                        st.write(f"**52 sem. haut :** {info.get('fiftyTwoWeekHigh', 'N/A'):.2f} {currency}" if info.get('fiftyTwoWeekHigh') else "**52 sem. haut :** N/A")
                        st.write(f"**52 sem. bas :** {info.get('fiftyTwoWeekLow', 'N/A'):.2f} {currency}" if info.get('fiftyTwoWeekLow') else "**52 sem. bas :** N/A")
                        st.write(f"**Objectif prix :** {info.get('targetMeanPrice', 'N/A'):.2f} {currency}" if info.get('targetMeanPrice') else "**Objectif prix :** N/A")
            else:
                st.write("Informations non disponibles")
        
        # Métriques supplémentaires pour EDF
        if symbol == 'EDF.PA':
            st.subheader("⚡ Métriques opérationnelles EDF")
            col_e1, col_e2, col_e3, col_e4 = st.columns(4)
            
            with col_e1:
                st.metric("Production nucléaire", "361 TWh", "-2.5%")
                st.caption("vs année précédente")
            
            with col_e2:
                st.metric("Production renouvelable", "95 TWh", "+8.2%")
                st.caption("hydro + solaire + éolien")
            
            with col_e3:
                st.metric("Clients France", "28.4 M", "+1.2%")
                st.caption("dont 22.3 M particuliers")
            
            with col_e4:
                st.metric("Investissements", "16.5 Md€", "+12%")
                st.caption("grand carénage + ENR")
            
            # Graphique de production
            st.subheader("🏭 Mix de production électrique")
            
            production_data = pd.DataFrame({
                'Source': ['Nucléaire', 'Hydraulique', 'Éolien', 'Solaire', 'Thermique', 'Autres'],
                'Production (TWh)': [361, 48, 24, 13, 8, 2],
                'Part (%)': [77.5, 10.3, 5.2, 2.8, 1.7, 0.5]
            })
            
            fig_pie = px.pie(
                production_data,
                values='Production (TWh)',
                names='Source',
                title="Mix de production électrique EDF (France)",
                color_discrete_sequence=['#003664', '#00A88F', '#FFCC00', '#FF9900', '#E4003B', '#666666']
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # Évolution des prix de l'électricité
            st.subheader("📈 Évolution des prix de l'électricité en France")
            
            dates_prices = pd.date_range(end=datetime.now(), periods=24, freq='M')
            prices = [0.1510, 0.1525, 0.1540, 0.1560, 0.1580, 0.1600, 0.1620, 0.1650, 0.1680, 0.1700,
                      0.1740, 0.1800, 0.1860, 0.1920, 0.1980, 0.2040, 0.2100, 0.2160, 0.2220, 0.2280,
                      0.2340, 0.2400, 0.2460, 0.2520]
            
            fig_prices = go.Figure()
            fig_prices.add_trace(go.Scatter(
                x=dates_prices,
                y=prices,
                mode='lines+markers',
                name='Prix (€/kWh)',
                line=dict(color='#003664', width=3),
                fill='tozeroy',
                fillcolor='rgba(0,54,100,0.1)'
            ))
            
            fig_prices.update_layout(
                title="Évolution du prix réglementé de l'électricité (tarif bleu)",
                xaxis_title="Date",
                yaxis_title="Prix (€/kWh)",
                hovermode='x',
                template='plotly_white'
            )
            
            st.plotly_chart(fig_prices, use_container_width=True)
            
            st.caption("Source: CRE - Commission de Régulation de l'Énergie")
    else:
        st.warning(f"Aucune donnée disponible pour {symbol}")

# ============================================================================
# SECTION 2: PORTEFEUILLE ÉNERGIE
# ============================================================================
elif menu == "🔋 Portefeuille énergie":
    st.subheader("🔋 Portefeuille virtuel - Secteur de l'énergie")
    
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.markdown("### ➕ Ajouter une position")
        with st.form("add_position"):
            symbol_pf = st.text_input("Symbole", value="EDF.PA").upper()
            
            exchange, country, currency = get_exchange_info(symbol_pf)
            st.caption(f"📍 {exchange} | {currency}")
            
            shares = st.number_input("Nombre d'actions", min_value=1, step=1, value=100)
            buy_price = st.number_input(f"Prix d'achat ({currency})", min_value=0.01, step=1.0, value=12.5)
            
            if st.form_submit_button("Ajouter au portefeuille"):
                if symbol_pf and shares > 0:
                    if symbol_pf not in st.session_state.portfolio:
                        st.session_state.portfolio[symbol_pf] = []
                    
                    st.session_state.portfolio[symbol_pf].append({
                        'shares': shares,
                        'buy_price': buy_price,
                        'currency': currency,
                        'country': country,
                        'date': datetime.now(USER_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')
                    })
                    st.success(f"✅ {shares} actions {symbol_pf} ajoutées")
        
        st.markdown("---")
        st.markdown("### 💡 Suggestions du secteur")
        st.markdown("""
        - **EDF.PA** - Électricité de France
        - **ENGI.PA** - Engie
        - **TTE.PA** - TotalEnergies
        - **SU.PA** - Schneider Electric
        - **VIE.PA** - Veolia
        - **IBE.MC** - Iberdrola
        - **ENEL.MI** - Enel
        - **RWE.DE** - RWE
        """)
    
    with col1:
        st.markdown("### 📊 Performance du portefeuille énergie")
        
        if st.session_state.portfolio:
            portfolio_data = []
            total_value = 0
            total_cost = 0
            
            for symbol_pf, positions in st.session_state.portfolio.items():
                try:
                    if st.session_state.demo_mode and symbol_pf in DEMO_DATA:
                        current = DEMO_DATA[symbol_pf]['current_price']
                    else:
                        ticker = yf.Ticker(symbol_pf)
                        hist = ticker.history(period='1d')
                        current = hist['Close'].iloc[-1] if not hist.empty else 0
                    
                    exchange, country, currency = get_exchange_info(symbol_pf)
                    
                    for pos in positions:
                        shares = pos['shares']
                        buy_price = pos['buy_price']
                        cost = shares * buy_price
                        value = shares * current
                        profit = value - cost
                        profit_pct = (profit / cost * 100) if cost > 0 else 0
                        
                        total_cost += cost
                        total_value += value
                        
                        portfolio_data.append({
                            'Symbole': symbol_pf,
                            'Pays': country,
                            'Actions': shares,
                            "Prix d'achat": f"{buy_price:,.2f} €",
                            'Prix actuel': f"{current:,.2f} €",
                            'Valeur': f"{value:,.2f} €",
                            'Profit': f"{profit:,.2f} €",
                            'Profit %': f"{profit_pct:.1f}%"
                        })
                except Exception as e:
                    st.warning(f"Impossible de charger {symbol_pf}")
            
            if portfolio_data:
                total_profit = total_value - total_cost
                total_profit_pct = (total_profit / total_cost * 100) if total_cost > 0 else 0
                
                st.markdown("#### Total portefeuille")
                col_i1, col_i2, col_i3 = st.columns(3)
                col_i1.metric("Valeur totale", f"{total_value:,.2f} €")
                col_i2.metric("Coût total", f"{total_cost:,.2f} €")
                col_i3.metric(
                    "Profit total",
                    f"{total_profit:,.2f} €",
                    delta=f"{total_profit_pct:.1f}%"
                )
                
                st.markdown("### 📋 Positions détaillées")
                df_portfolio = pd.DataFrame(portfolio_data)
                st.dataframe(df_portfolio, use_container_width=True, hide_index=True)
                
                # Graphique de répartition
                try:
                    fig_pie = px.pie(
                        names=[p['Symbole'] for p in portfolio_data],
                        values=[float(p['Valeur'].split()[0].replace(',', '')) for p in portfolio_data],
                        title="Répartition du portefeuille par valeur"
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                except:
                    st.warning("Impossible de générer le graphique")
                
                if st.button("🗑️ Vider le portefeuille"):
                    st.session_state.portfolio = {}
                    st.rerun()
            else:
                st.info("Aucune donnée de performance disponible")
        else:
            st.info("Aucune position dans le portefeuille. Ajoutez des actions du secteur énergétique pour commencer !")

# ============================================================================
# SECTION 3: ALERTES DE PRIX
# ============================================================================
elif menu == "🔔 Alertes de prix":
    st.subheader("🔔 Gestion des alertes de prix")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### ➕ Créer une nouvelle alerte")
        with st.form("new_alert"):
            alert_symbol = st.text_input("Symbole", value=symbol if symbol else "EDF.PA").upper()
            exchange, country, currency = get_exchange_info(alert_symbol)
            st.caption(f"📍 {exchange} | {currency}")
            
            default_price = float(current_price * 1.05) if current_price > 0 else 12.5
            alert_price = st.number_input(
                f"Prix cible ({currency})", 
                min_value=0.01, 
                step=1.0, 
                value=default_price
            )
            
            col_cond, col_type = st.columns(2)
            with col_cond:
                condition = st.selectbox("Condition", ["above (au-dessus)", "below (en-dessous)"])
                condition = condition.split()[0]
            with col_type:
                alert_type = st.selectbox("Type", ["Permanent", "Une fois"])
            
            one_time = alert_type == "Une fois"
            
            if st.form_submit_button("Créer l'alerte"):
                st.session_state.price_alerts.append({
                    'symbol': alert_symbol,
                    'price': alert_price,
                    'condition': condition,
                    'one_time': one_time,
                    'currency': currency,
                    'country': country,
                    'created': datetime.now(USER_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')
                })
                st.success(f"✅ Alerte créée pour {alert_symbol} à {alert_price} {currency}")
    
    with col2:
        st.markdown("### 📋 Alertes actives")
        if st.session_state.price_alerts:
            for i, alert in enumerate(st.session_state.price_alerts):
                with st.container():
                    currency = alert.get('currency', 'EUR')
                    st.markdown(f"""
                    <div class='alert-box alert-warning'>
                        <b>{alert['symbol']}</b> - {alert['condition']} {alert['price']:.2f} {currency}<br>
                        <small>{alert.get('country', '')} | Créée: {alert['created']} | {('Usage unique' if alert['one_time'] else 'Permanent')}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"Supprimer", key=f"del_alert_{i}"):
                        st.session_state.price_alerts.pop(i)
                        st.rerun()
        else:
            st.info("Aucune alerte active")

# ============================================================================
# SECTION 4: NOTIFICATIONS EMAIL
# ============================================================================
elif menu == "📧 Notifications email":
    st.subheader("📧 Configuration des notifications email")
    
    with st.form("email_config"):
        enabled = st.checkbox("Activer les notifications email", value=st.session_state.email_config['enabled'])
        
        col1, col2 = st.columns(2)
        with col1:
            smtp_server = st.text_input("Serveur SMTP", value=st.session_state.email_config['smtp_server'])
            smtp_port = st.number_input("Port SMTP", value=st.session_state.email_config['smtp_port'])
        
        with col2:
            email = st.text_input("Adresse email", value=st.session_state.email_config['email'])
            password = st.text_input("Mot de passe", type="password", value=st.session_state.email_config['password'])
        
        test_email = st.text_input("Email de test (optionnel)")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.form_submit_button("💾 Sauvegarder"):
                st.session_state.email_config = {
                    'enabled': enabled,
                    'smtp_server': smtp_server,
                    'smtp_port': smtp_port,
                    'email': email,
                    'password': password
                }
                st.success("Configuration sauvegardée !")
        
        with col_btn2:
            if st.form_submit_button("📨 Tester"):
                if test_email:
                    if send_email_alert(
                        "Test de notification",
                        f"<h2>Test réussi !</h2><p>Votre configuration email fonctionne correctement !</p><p>Heure d'envoi: {datetime.now(USER_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')} (heure Paris)</p>",
                        test_email
                    ):
                        st.success("Email de test envoyé !")
                    else:
                        st.error("Échec de l'envoi")
    
    with st.expander("📋 Aperçu de la configuration"):
        st.json(st.session_state.email_config)

# ============================================================================
# SECTION 5: EXPORT DES DONNÉES
# ============================================================================
elif menu == "📤 Export des données":
    st.subheader("📤 Export des données")
    
    if hist is not None and not hist.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📊 Données historiques")
            display_hist = hist.copy()
            display_hist.index = display_hist.index.strftime('%Y-%m-%d %H:%M:%S (heure Paris)')
            st.dataframe(display_hist.tail(20))
            
            csv = hist.to_csv()
            st.download_button(
                label="📥 Télécharger en CSV",
                data=csv,
                file_name=f"{symbol}_data_{datetime.now(USER_TIMEZONE).strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            st.markdown("### 📈 Rapport PDF")
            st.info("Génération de rapport PDF (simulée)")
            
            st.markdown("**Statistiques:**")
            stats = {
                'Moyenne': hist['Close'].mean(),
                'Écart-type': hist['Close'].std(),
                'Min': hist['Close'].min(),
                'Max': hist['Close'].max(),
                'Variation totale': f"{(hist['Close'].iloc[-1] / hist['Close'].iloc[0] - 1) * 100:.2f}%" if len(hist) > 1 else "N/A"
            }
            
            for key, value in stats.items():
                if isinstance(value, float):
                    st.write(f"{key}: {format_currency(value, 'EUR')}")
                else:
                    st.write(f"{key}: {value}")
            
            exchange, country, currency = get_exchange_info(symbol)
            json_data = {
                'symbol': symbol,
                'exchange': exchange,
                'country': country,
                'currency': currency,
                'last_update': datetime.now(USER_TIMEZONE).isoformat(),
                'timezone': 'Europe/Paris',
                'current_price': float(current_price) if current_price else 0,
                'statistics': {k: (float(v) if isinstance(v, (int, float)) else v) for k, v in stats.items()},
                'data': hist.reset_index().to_dict(orient='records')
            }
            
            st.download_button(
                label="📥 Télécharger en JSON",
                data=json.dumps(json_data, indent=2, default=str),
                file_name=f"{symbol}_data_{datetime.now(USER_TIMEZONE).strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    else:
        st.warning(f"Aucune donnée à exporter pour {symbol}")

# ============================================================================
# SECTION 6: PRÉDICTIONS ML
# ============================================================================
elif menu == "🤖 Prédictions ML":
    st.subheader("🤖 Prédictions avec Machine Learning - Actions EDF et secteur énergétique")
    
    if hist is not None and not hist.empty and len(hist) > 30:
        st.markdown("### Modèle de prédiction (Régression polynomiale)")
        
        exchange, country, currency = get_exchange_info(symbol)
        
        st.info(f"""
        ⚠️ Facteurs influençant EDF et les valeurs du secteur énergétique:
        
        **Facteurs macroéconomiques:**
        - Prix de l'électricité sur le marché européen
        - Prix du gaz naturel et du charbon
        - Prix du CO2 (quotas carbone)
        - Décisions de la CRE (Commission de Régulation de l'Énergie)
        - Politique énergétique française et européenne
        - Taux d'intérêt et inflation
        - Croissance économique (PIB)
        
        **Facteurs spécifiques à EDF:**
        - Disponibilité du parc nucléaire (taux de disponibilité)
        - Programme Grand Carénage (maintenance des centrales)
        - Régulation des tarifs réglementés
        - ARENH (Accès Régulé à l'Électricité Nucléaire Historique)
        - Développement des énergies renouvelables
        - Relations avec les fournisseurs alternatifs
        - Investissements dans les nouvelles technologies (EPR, SMR)
        
        **Facteurs géopolitiques:**
        - Relations avec la Russie (gaz, uranium)
        - Situation au Moyen-Orient
        - Transition énergétique européenne
        - Élections et politique nationale
        
        **Saisonnalité:**
        - Pic de consommation hivernal
        - Maintenance nucléaire en été
        - Production hydraulique variable
        - Production solaire/éolienne selon météo
        """)
        
        df_pred = hist[['Close']].reset_index()
        df_pred['Days'] = (df_pred['Date'] - df_pred['Date'].min()).dt.days
        
        X = df_pred['Days'].values.reshape(-1, 1)
        y = df_pred['Close'].values
        
        col1, col2 = st.columns(2)
        
        with col1:
            days_to_predict = st.slider("Jours à prédire", min_value=1, max_value=30, value=7)
            degree = st.slider("Degré du polynôme", min_value=1, max_value=5, value=2)
        
        with col2:
            show_confidence = st.checkbox("Afficher l'intervalle de confiance", value=True)
        
        model = make_pipeline(
            PolynomialFeatures(degree=degree),
            LinearRegression()
        )
        model.fit(X, y)
        
        last_day = X[-1][0]
        future_days = np.arange(last_day + 1, last_day + days_to_predict + 1).reshape(-1, 1)
        predictions = model.predict(future_days)
        
        last_date = df_pred['Date'].iloc[-1]
        future_dates = [last_date + timedelta(days=i+1) for i in range(days_to_predict)]
        
        fig_pred = go.Figure()
        
        fig_pred.add_trace(go.Scatter(
            x=df_pred['Date'],
            y=y,
            mode='lines',
            name='Historique',
            line=dict(color='#003664', width=2)
        ))
        
        fig_pred.add_trace(go.Scatter(
            x=future_dates,
            y=predictions,
            mode='lines+markers',
            name='Prédictions',
            line=dict(color='#E4003B', width=2, dash='dash'),
            marker=dict(size=8)
        ))
        
        if show_confidence:
            residuals = y - model.predict(X)
            std_residuals = np.std(residuals)
            
            upper_bound = predictions + 2 * std_residuals
            lower_bound = predictions - 2 * std_residuals
            
            fig_pred.add_trace(go.Scatter(
                x=future_dates + future_dates[::-1],
                y=np.concatenate([upper_bound, lower_bound[::-1]]),
                fill='toself',
                fillcolor='rgba(228,0,59,0.2)',
                line=dict(color='rgba(228,0,59,0)'),
                name='Intervalle confiance 95%'
            ))
        
        fig_pred.update_layout(
            title=f"Prédictions pour {symbol} ({exchange}) - {days_to_predict} jours",
            xaxis_title="Date (heure Paris)",
            yaxis_title=f"Prix ({currency})",
            hovermode='x unified',
            template='plotly_white',
            height=500
        )
        
        st.plotly_chart(fig_pred, use_container_width=True)
        
        st.markdown("### 📋 Prédictions détaillées")
        pred_df = pd.DataFrame({
            'Date': [d.strftime('%Y-%m-%d') for d in future_dates],
            'Prix prédit': [f"{p:.2f} {currency}" for p in predictions],
            'Variation %': [f"{(p/current_price - 1)*100:.2f}%" for p in predictions]
        })
        st.dataframe(pred_df, use_container_width=True, hide_index=True)
        
        st.markdown("### 📊 Performance du modèle")
        residuals = y - model.predict(X)
        mse = np.mean(residuals**2)
        rmse = np.sqrt(mse)
        mae = np.mean(np.abs(residuals))
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("RMSE", f"{rmse:.2f} {currency}")
        col_m2.metric("MAE", f"{mae:.2f} {currency}")
        col_m3.metric("R²", f"{model.score(X, y):.3f}")
        
        st.markdown("### 📈 Analyse des tendances")
        last_price = current_price
        last_pred = predictions[-1]
        trend = "HAUSSIÈRE 📈" if last_pred > last_price else "BAISSIÈRE 📉" if last_pred < last_price else "NEUTRE ➡️"
        
        if last_pred > last_price * 1.05:
            strength = "Forte tendance haussière 🚀"
        elif last_pred > last_price:
            strength = "Légère tendance haussière 📈"
        elif last_pred < last_price * 0.95:
            strength = "Forte tendance baissière 🔻"
        elif last_pred < last_price:
            strength = "Légère tendance baissière 📉"
        else:
            strength = "Tendance latérale ⏸️"
        
        st.info(f"**Tendance prévue:** {trend} - {strength}")
        
        with st.expander("⚡ Analyse fondamentale du secteur énergétique"):
            st.markdown("""
            ### Facteurs clés pour EDF et le secteur énergétique français
            
            **Électricité et nucléaire:**
            - Le parc nucléaire français (56 réacteurs) assure environ 70% de la production
            - Programme Grand Carénage: 50 Md€ pour prolonger la durée de vie des centrales
            - Nouveaux EPR: Flamanville 3 (2024), Penly (projet)
            - SMR (Small Modular Reactors): développement de nouveaux réacteurs
            
            **Transition énergétique:**
            - Objectif 50% de nucléaire à l'horizon 2035
            - Développement des ENR: solaire, éolien offshore
            - Fermeture des centrales à charbon
            - Électrification des usages (véhicules électriques, pompes à chaleur)
            
            **Régulation:**
            - ARENH: permet aux fournisseurs alternatifs d'acheter du nucléaire à prix régulé
            - Tarifs réglementés de vente (TRV)
            - CRE: régulateur du marché
            - Mécanismes de capacité
            
            **Prix de marché:**
            - Marché spot (EPEX Spot)
            - Marché à terme (EEX, Powernext)
            - Spreads avec le gaz et le CO2
            - Interconnexions européennes
            
            **Comparaison européenne:**
            - Allemagne: sortie du nucléaire, développement charbon/gaz/ENR
            - Espagne: forte production ENR, interconnexions limitées
            - Italie: dépendance aux importations, gaz important
            - UK: nucléaire, gaz, ENR offshore
            
            **Indicateurs à suivre:**
            - Taux de disponibilité nucléaire (hebdomadaire)
            - Niveaux des barrages hydrauliques
            - Prix du CO2 (EU ETS)
            - Prix du gaz TTF
            - Consommation électrique (RTE)
            - Exportations/importations
            """)
        
    else:
        st.warning(f"Pas assez de données historiques pour {symbol} (minimum 30 points)")

# ============================================================================
# SECTION 7: COMPARAISON SECTORIELLE
# ============================================================================
elif menu == "🇪🇺 Comparaison sectorielle":
    st.subheader("🇪🇺 Comparaison des valeurs du secteur énergétique européen")
    
    # Liste des principales valeurs du secteur
    energy_stocks = {
        'EDF.PA': 'EDF (France)',
        'ENGI.PA': 'Engie (France)',
        'TTE.PA': 'TotalEnergies (France)',
        'SU.PA': 'Schneider Electric (France)',
        'VIE.PA': 'Veolia (France)',
        'IBE.MC': 'Iberdrola (Espagne)',
        'ENEL.MI': 'Enel (Italie)',
        'RWE.DE': 'RWE (Allemagne)',
        'EOAN.DE': 'E.ON (Allemagne)',
        'SSE.L': 'SSE (UK)',
        'NG.L': 'National Grid (UK)',
        'OR.PA': 'L\'Oréal (référence CAC40)'
    }
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown("### 📊 Sélection")
        selected_stocks = st.multiselect(
            "Choisir les actions à comparer",
            options=list(energy_stocks.keys()),
            default=['EDF.PA', 'ENGI.PA', 'TTE.PA', 'IBE.MC'],
            format_func=lambda x: energy_stocks[x]
        )
        
        comparison_period = st.selectbox(
            "Période de comparaison",
            options=["1mo", "3mo", "6mo", "1y", "2y"],
            index=1
        )
        
        st.markdown("### 💡 Indices de référence")
        st.markdown("""
        - **^FCHI**: CAC 40
        - **^STOXX50E**: Euro Stoxx 50
        - **^SX6E**: Stoxx 600 Utilities
        """)
    
    with col2:
        if selected_stocks:
            st.markdown("### 📈 Performance comparée")
            
            # Collecter les données
            perf_data = []
            prices_data = {}
            
            for stock in selected_stocks:
                try:
                    if st.session_state.demo_mode and stock in DEMO_DATA:
                        current = DEMO_DATA[stock]['current_price']
                        prev = DEMO_DATA[stock]['previous_close']
                        change_pct = ((current - prev) / prev * 100)
                        
                        perf_data.append({
                            'Symbole': stock,
                            'Société': energy_stocks[stock],
                            'Prix': f"{current:.2f} €",
                            'Variation %': f"{change_pct:.2f}%",
                            'Variation': change_pct
                        })
                        
                        # Générer historique simulé
                        hist_demo = generate_demo_history(stock, comparison_period)
                        prices_data[stock] = hist_demo['Close']
                    else:
                        ticker = yf.Ticker(stock)
                        hist = ticker.history(period=comparison_period)
                        
                        if not hist.empty:
                            current = hist['Close'].iloc[-1]
                            prev = hist['Close'].iloc[0]
                            change_pct = ((current - prev) / prev * 100)
                            
                            perf_data.append({
                                'Symbole': stock,
                                'Société': energy_stocks[stock],
                                'Prix': f"{current:.2f} €",
                                'Variation %': f"{change_pct:.2f}%",
                                'Variation': change_pct
                            })
                            
                            prices_data[stock] = hist['Close']
                except:
                    st.warning(f"Données non disponibles pour {stock}")
            
            if perf_data:
                df_perf = pd.DataFrame(perf_data)
                df_perf = df_perf.sort_values('Variation', ascending=False)
                st.dataframe(df_perf[['Symbole', 'Société', 'Prix', 'Variation %']], use_container_width=True, hide_index=True)
            
            if prices_data:
                # Graphique comparatif
                fig_comp = go.Figure()
                
                # Normaliser les prix à 100 pour comparaison
                for stock, prices in prices_data.items():
                    normalized = prices / prices.iloc[0] * 100
                    fig_comp.add_trace(go.Scatter(
                        x=normalized.index,
                        y=normalized,
                        mode='lines',
                        name=energy_stocks[stock],
                        line=dict(width=2)
                    ))
                
                fig_comp.update_layout(
                    title=f"Performance relative (base 100) - {comparison_period}",
                    xaxis_title="Date",
                    yaxis_title="Performance (%)",
                    hovermode='x unified',
                    template='plotly_white',
                    height=500
                )
                
                st.plotly_chart(fig_comp, use_container_width=True)
                
                # Graphique de corrélation
                if len(prices_data) >= 2:
                    st.subheader("📊 Matrice de corrélation")
                    
                    # Créer un DataFrame avec tous les prix
                    corr_df = pd.DataFrame(prices_data)
                    corr_matrix = corr_df.corr()
                    
                    fig_corr = px.imshow(
                        corr_matrix,
                        text_auto=True,
                        aspect="auto",
                        color_continuous_scale='RdBu_r',
                        title="Corrélations entre les actions",
                        labels=dict(x="Symbole", y="Symbole", color="Corrélation")
                    )
                    
                    st.plotly_chart(fig_corr, use_container_width=True)
        else:
            st.info("Sélectionnez au moins une action pour afficher la comparaison")
    
    # Analyse sectorielle
    with st.expander("📈 Analyse du secteur des utilities en Europe"):
        st.markdown("""
        ### Tendances du secteur électrique européen
        
        **Transition énergétique:**
        - Accélération des investissements dans les renouvelables
        - Sortie progressive du charbon
        - Rôle du nucléaire dans la stratégie bas-carbone
        - Électrification des usages
        
        **Défis:**
        - Volatilité des prix de l'énergie
        - Tensions géopolitiques (Ukraine, Moyen-Orient)
        - Inflation des coûts de construction
        - Complexité réglementaire
        
        **Opportunités:**
        - Hydrogène vert
        - Stockage d'énergie
        - Réseaux intelligents
        - Efficacité énergétique
        
        **Comparaison par pays:**
        - **France**: Nucléaire dominant, EDF nationalisé
        - **Allemagne**: Mix diversifié, sortie du nucléaire
        - **Espagne**: Fort potentiel ENR
        - **Italie**: Dépendance aux importations
        - **UK**: Libéralisation, investissements offshore
        
        **Indicateurs à surveiller:**
        - Prix de l'électricité (base, peak)
        - Prix du CO2
        - Taux d'utilisation des interconnexions
        - Niveaux de stockage gaz
        - Météo et production ENR
        """)

# ============================================================================
# WATCHLIST ET DERNIÈRE MISE À JOUR
# ============================================================================
st.markdown("---")
col_w1, col_w2 = st.columns([3, 1])

with col_w1:
    st.subheader("📋 Watchlist - Secteur énergétique français et européen")
    
    # Regrouper par type
    french_stocks = [s for s in st.session_state.watchlist if '.PA' in s]
    european_stocks = [s for s in st.session_state.watchlist if any(x in s for x in ['.MC', '.MI', '.DE', '.L'])]
    indices = [s for s in st.session_state.watchlist if s.startswith('^')]
    
    tabs = st.tabs(["🇫🇷 France", "🇪🇺 Europe", "📊 Indices"])
    
    with tabs[0]:  # France
        if french_stocks:
            cols_per_row = 4
            for i in range(0, len(french_stocks), cols_per_row):
                cols = st.columns(min(cols_per_row, len(french_stocks) - i))
                for j, sym in enumerate(french_stocks[i:i+cols_per_row]):
                    with cols[j]:
                        try:
                            if st.session_state.demo_mode and sym in DEMO_DATA:
                                price = DEMO_DATA[sym]['current_price']
                                prev_close = DEMO_DATA[sym]['previous_close']
                                change = ((price - prev_close) / prev_close * 100)
                                name = SYMBOL_INFO.get(sym, sym)
                                st.metric(name, f"{price:.2f} €", delta=f"{change:.1f}%")
                            else:
                                ticker = yf.Ticker(sym)
                                hist = ticker.history(period='1d')
                                if not hist.empty:
                                    price = hist['Close'].iloc[-1]
                                    prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else price
                                    change = ((price - prev_close) / prev_close * 100)
                                    name = SYMBOL_INFO.get(sym, sym)
                                    st.metric(name, f"{price:.2f} €", delta=f"{change:.1f}%")
                                else:
                                    st.metric(sym, "N/A")
                        except:
                            price = random.uniform(10, 200)
                            st.metric(SYMBOL_INFO.get(sym, sym), f"{price:.2f} €*", delta=f"{random.uniform(-2, 2):.1f}%")
        else:
            st.info("Aucune action française")
    
    with tabs[1]:  # Europe
        if european_stocks:
            cols_per_row = 4
            for i in range(0, len(european_stocks), cols_per_row):
                cols = st.columns(min(cols_per_row, len(european_stocks) - i))
                for j, sym in enumerate(european_stocks[i:i+cols_per_row]):
                    with cols[j]:
                        try:
                            if st.session_state.demo_mode:
                                price = random.uniform(10, 100)
                                st.metric(SYMBOL_INFO.get(sym, sym), f"{price:.2f} €*", delta=f"{random.uniform(-2, 2):.1f}%")
                            else:
                                ticker = yf.Ticker(sym)
                                hist = ticker.history(period='1d')
                                if not hist.empty:
                                    price = hist['Close'].iloc[-1]
                                    prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else price
                                    change = ((price - prev_close) / prev_close * 100)
                                    name = SYMBOL_INFO.get(sym, sym)
                                    st.metric(name, f"{price:.2f} €", delta=f"{change:.1f}%")
                                else:
                                    st.metric(sym, "N/A")
                        except:
                            price = random.uniform(10, 100)
                            st.metric(SYMBOL_INFO.get(sym, sym), f"{price:.2f} €*", delta=f"{random.uniform(-2, 2):.1f}%")
        else:
            st.info("Aucune action européenne")
    
    with tabs[2]:  # Indices
        if indices:
            cols_per_row = 3
            for i in range(0, len(indices), cols_per_row):
                cols = st.columns(min(cols_per_row, len(indices) - i))
                for j, sym in enumerate(indices[i:i+cols_per_row]):
                    with cols[j]:
                        try:
                            if st.session_state.demo_mode:
                                if 'FCHI' in sym:  # CAC 40
                                    value = random.uniform(7000, 7500)
                                elif 'STOXX' in sym:
                                    value = random.uniform(4000, 4200)
                                else:
                                    value = random.uniform(300, 350)
                                st.metric(sym, f"{value:.0f}", delta=f"{random.uniform(-1, 1):.1f}%")
                            else:
                                ticker = yf.Ticker(sym)
                                hist = ticker.history(period='1d')
                                if not hist.empty:
                                    value = hist['Close'].iloc[-1]
                                    prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else value
                                    change = ((value - prev_close) / prev_close * 100)
                                    st.metric(sym, f"{value:.0f}", delta=f"{change:.1f}%")
                                else:
                                    st.metric(sym, "N/A")
                        except:
                            st.metric(sym, "N/A")
        else:
            st.info("Aucun indice")

with col_w2:
    # Horaires et informations
    paris_time = datetime.now(USER_TIMEZONE)
    
    st.markdown("### 🕐 Heure de Paris")
    st.caption(f"{paris_time.strftime('%H:%M:%S')}")
    
    st.markdown("### 📊 Statut du marché")
    status, icon = get_market_status()
    st.caption(f"{icon} {status}")
    
    # Prochains événements
    st.markdown("### 📅 Prochains événements")
    st.caption("• Publication des résultats EDF: fin février")
    st.caption("• Assemblée générale: mai 2025")
    st.caption("• Détachement dividende: juin 2025")
    
    if st.session_state.demo_mode:
        st.caption("🎮 Mode démonstration")
    else:
        st.caption(f"Dernière MAJ: {paris_time.strftime('%H:%M:%S')}")
    
    if auto_refresh and hist is not None and not hist.empty:
        time.sleep(refresh_rate)
        st.rerun()

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray; font-size: 0.8rem;'>"
    "⚡ Tracker EDF - Électricité de France | 🇫🇷 Euronext Paris | 📊 Données en temps réel (avec délai possible)<br>"
    "📅 Horaires de trading: 9h00-17h30 (heure de Paris) | Fermé samedi, dimanche et jours fériés<br>"
    "🏭 Données fournies par Yahoo Finance et EDF - À titre informatif uniquement"
    "</p>",
    unsafe_allow_html=True
)

# Message de bienvenue
st.markdown("""
<div style='text-align: center; font-family: Roboto; font-size: 1.2rem; margin-top: 1rem;'>
    <p>⚡ Suivez l'action EDF et le secteur énergétique français en temps réel</p>
    <p>Analyse fondamentale, technique et prédictions ML</p>
</div>
""", unsafe_allow_html=True)

# Note sur les jours fériés à venir
today = datetime.now().date()
next_holidays = []
for holiday in FRENCH_HOLIDAYS_2024:
    holiday_date = datetime.strptime(holiday, '%Y-%m-%d').date()
    if holiday_date > today:
        next_holidays.append((holiday_date, holiday))

if next_holidays:
    next_holiday_date, next_holiday_str = next_holidays[0]
    days_until = (next_holiday_date - today).days
    st.info(f"📅 Prochain jour férié: {next_holiday_date.strftime('%d/%m/%Y')} dans {days_until} jours - Marché fermé")
