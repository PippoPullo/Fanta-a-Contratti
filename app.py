import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="FantaGestionale", layout="wide")

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# Controllo integrità Database per i Rinnovi
try:
    supabase.table("players").select("future_salary").limit(1).execute()
except Exception as e:
    st.error("⚠️ **AGGIORNAMENTO DATABASE RICHIESTO PER I RINNOVI!** Vai nell'SQL Editor di Supabase ed esegui questo comando (copia e incolla):")
    st.code("ALTER TABLE public.players ADD COLUMN IF NOT EXISTS future_salary INTEGER;\nALTER TABLE public.players ADD COLUMN IF NOT EXISTS future_contract_years INTEGER;", language="sql")

def get_rules(season_name="2026/2027"):
    try:
        res = supabase.table("league_rules").select("*").eq("season", season_name).execute()
        if res.data:
            return res.data[0]
        else:
            res_all = supabase.table("league_rules").select("*").limit(1).execute()
            if res_all.data:
                return res_all.data[0]
    except:
        pass
    return {
        "season": "2026/2027",
        "tranche_value": 120,
        "salary_cap": 315,
        "max_contract_years": 55,
        "bonus_base": 5,
        "bonus_medio": 10,
        "bonus_top": 15,
        "bonus_advanced": 20,
        "maint_base": 2,
        "maint_medio": 5,
        "maint_top": 10,
        "maint_advanced": 15,
        "paracadute_1": 15,
        "paracadute_2": 10,
        "paracadute_3": 5
    }

active_season = "2026/2027"
rules = get_rules(active_season)

def calcola_gol(score):
    if score < 66:
        return 0
    return int((score - 66) // 4) + 1

def calcola_10_percento(valore):
    bonus = float(valore) * 0.1
    parte_decimale = bonus - int(bonus)
    risultato = int(bonus) if parte_decimale <= 0.5 else int(bonus) + 1
    return max(1, int(risultato))

def registra_snapshot_finanziario(team_id, etichetta, saldo_attuale):
    try:
        supabase.table("financial_history").insert({
            "team_id": team_id,
            "season": active_season,
            "event_label": etichetta,
            "balance_snapshot": int(round(saldo_attuale))
        }).execute()
    except:
        pass

def check_is_abroad(player_dict):
    if not player_dict:
        return False
    return bool(player_dict.get('is_abroad', False)) or str(player_dict.get('serie_a_team', '')).strip().lower() == 'estero'

ROLE_ORDER_LIST = ["POR", "DS", "DC", "DD", "B", "M", "C", "E", "W", "T", "A", "PC"]
ROLE_PRIORITY = {r: idx for idx, r in enumerate(ROLE_ORDER_LIST)}
ROLE_PRIORITY["P"] = 0

def get_player_role_priority(role_str):
    if not role_str:
        return 999
    roles = [r.strip().upper() for r in str(role_str).replace('/', ',').replace(';', ',').split(',')]
    priorities = [ROLE_PRIORITY.get(r, 999) for r in roles if r]
    return min(priorities) if priorities else 999

def render_role_badge(role_str):
    if not role_str:
        return ""
    
    def get_color_for_single_role(r):
        if r in ['POR', 'P']:
            return '#f39c12'
        elif r in ['DC', 'B', 'DS', 'DD']:
            return '#27ae60'
        elif r in ['M', 'C', 'E']:
            return '#2980b9'
        elif r in ['T', 'W']:
            return '#8e44ad'
        elif r in ['A', 'PC']:
            return '#c0392b'
        return '#7f8c8d'

    roles = [r.strip().upper() for r in str(role_str).replace('/', ',').replace(';', ',').split(',') if r.strip()]
    colors = []
    for r in roles:
        c = get_color_for_single_role(r)
        if c not in colors:
            colors.append(c)
            
    if not colors:
        colors = ['#7f8c8d']
        
    if len(colors) == 1:
        bg_style = f"background-color: {colors[0]};"
    else:
        c1, c2 = colors[0], colors[1]
        bg_style = f"background: linear-gradient(135deg, {c1} 50%, {c2} 50%);"
        
    display_text = "/".join(roles)
    return f'<span style="{bg_style} color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; margin-right: 6px; display: inline-block; text-align: center; text-shadow: 1px 1px 2px rgba(0,0,0,0.7);">{display_text}</span>'

# --- GESTIONE AUTENTICAZIONE E REGISTRAZIONE ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.is_admin = False
    st.session_state.team_id = None
    st.session_state.is_viewer = False

if "mostra_cocco" not in st.session_state:
    st.session_state.mostra_cocco = False

# Gestione Automatica Modalità Visitatore
if not st.session_state.authenticated and not st.session_state.is_viewer:
    st.session_state.is_viewer = True

with st.sidebar:
    if st.session_state.authenticated:
        st.write(f"Utente: **{st.session_state.username}**")
        if st.session_state.is_admin:
            st.info("🛠️ Ruolo: Amministratore")
        else:
            st.info("👤 Ruolo: Proprietario Squadra")
        if st.button("Disconnetti 🚪"):
            st.session_state.authenticated = False
            st.session_state.username = ""
            st.session_state.is_admin = False
            st.session_state.team_id = None
            st.session_state.is_viewer = True
            st.rerun()
    else:
        st.write("Utente: **Visitatore**")
        st.info("👁️ Ruolo: Sola Lettura")
        if st.button("🔑 Effettua Login per Modifiche"):
            st.session_state.show_login = True
            st.rerun()

if not st.session_state.authenticated and st.session_state.get("show_login", False):
    st.title("🔐 Accesso & Registrazione - FantaGestionale")
    
    tab_login, tab_register = st.tabs(["🔑 Accedi", "📝 Registra Nuova Squadra"])
    
    with tab_login:
        with st.form("login_form"):
            u_input = st.text_input("Username")
            p_input = st.text_input("Password", type="password")
            a_input = st.text_input("Password Admin (opzionale per poteri totali)", type="password")
            
            submit_login = st.form_submit_button("Accedi 🚀")
            
            if submit_login:
                ADMIN_SECRET_PWD = "FantaBrucone"
                
                teams_check = supabase.table("teams").select("*").execute().data
                matched_team = next((t for t in teams_check if t.get('username') == u_input and t.get('password') == p_input), None)
                
                if matched_team:
                    st.session_state.authenticated = True
                    st.session_state.username = u_input
                    st.session_state.team_id = matched_team['id']
                    st.session_state.is_viewer = False
                    st.session_state.show_login = False
                    if a_input == ADMIN_SECRET_PWD:
                        st.session_state.is_admin = True
                        st.success("Accesso effettuato come Amministratore!")
                    else:
                        st.session_state.is_admin = False
                        st.success(f"Accesso effettuato per la squadra: {matched_team['name']}")
                    st.rerun()
                else:
                    st.error("Credenziali non valide o username/password errati.")

        if st.button("Password dimenticata?"):
            st.session_state.mostra_cocco = True

        if st.session_state.mostra_cocco:
            st.info("SEI COCCO!")
            if st.button("Chiudi banner"):
                st.session_state.mostra_cocco = False
                st.rerun()
                    
        if st.button("⬅️ Torna alla modalità Visitatore"):
            st.session_state.show_login = False
            st.rerun()
                    
    with tab_register:
        st.write("Crea il profilo per la tua squadra inserendo i dati sottostanti:")
        with st.form("register_team_form"):
            reg_team_name = st.text_input("Nome della Squadra")
            reg_stadium = st.text_input("Nome dello Stadio", value="Stadio Comunale")
            reg_user = st.text_input("Scegli Username")
            reg_pass = st.text_input("Scegli Password", type="password")
            
            submit_reg = st.form_submit_button("Crea Squadra ✍️")
            
            if submit_reg:
                if not reg_team_name or not reg_user or not reg_pass:
                    st.error("Compila tutti i campi obbligatori.")
                else:
                    existing_user = supabase.table("teams").select("*").eq("username", reg_user).execute().data
                    if existing_user:
                        st.error("Questo Username è già occupato. Scegline un altro.")
                    else:
                        supabase.table("teams").insert({
                            "name": reg_team_name,
                            "stadium_name": reg_stadium,
                            "username": reg_user,
                            "password": reg_pass,
                            "balance": 500,
                            "u21_balance": 30,
                            "total_contract_years": 0,
                            "stadium_level": "Base",
                            "ranking": 1
                        }).execute()
                        st.success("🎉 Registrazione completata con successo! Ora puoi andare nella scheda 'Accedi' e fare il login.")
    st.stop()

# --- APPLICAZIONE PRINCIPALE ---
st.title("🏆 Dashboard Fantacalcio Manageriale")

with st.sidebar:
    st.write(f"📅 Stagione: **{active_season}**")

teams_res = supabase.table("teams").select("*").order("name").execute()
teams = teams_res.data
players_res = supabase.table("players").select("*").execute()
players = players_res.data
try:
    u21_res = supabase.table("u21_players").select("*").execute()
    u21_players = u21_res.data
except:
    u21_players = []

try:
    trades_res = supabase.table("trades").select("*").execute().data
except:
    trades_res = []

try:
    loans_res = supabase.table("loans").select("*").execute().data
except:
    loans_res = []

try:
    fin_history_res = supabase.table("financial_history").select("*").eq("season", active_season).execute().data
except:
    fin_history_res = []

# Definizione delle Tab Dinamiche in base all'utente
if st.session_state.is_admin:
    tab1, tab_free, tab3, tab4, tab5, tab6, tab7, tab_report, tab_hof, tab_reg, tab8 = st.tabs([
        "📊 Dashboard & Finanze", "🔎 Svincolati & Variazioni", "📋 Rose & Svincoli", 
        "👶 Panchina U21", "🤝 Scambi & Prestiti", "⚽ Inserimento Giornate", 
        "⚽ Mercato Admin", "📜 Report Attività", "🏛️ Albo d'Oro", "📖 Regolamento", "⚙️ Admin"
    ])
elif st.session_state.authenticated:
    tab1, tab_free, tab3, tab4, tab5, tab6, tab_report, tab_hof, tab_reg = st.tabs([
        "📊 Dashboard & Finanze", "🔎 Svincolati & Variazioni", "📋 La Mia Rosa & Previsioni", 
        "👶 Panchina U21", "🤝 Scambi & Prestiti", "⚽ Inserimento Giornate", 
        "📜 Report Attività", "🏛️ Albo d'Oro", "📖 Regolamento"
    ])
else:
    tab1, tab_free, tab3, tab_report, tab_hof, tab_reg = st.tabs([
        "📊 Dashboard & Finanze", "🔎 Svincolati & Variazioni", "📋 Rose delle Squadre", 
        "📜 Report Attività", "🏛️ Albo d'Oro", "📖 Regolamento"
    ])

# TAB 1: DASHBOARD, CLASSIFICA, MONTEPREMI & GRAFICO FINANZIARIO AVANZATO
with tab1:
    st.header("🏆 Classifica Ufficiale & Montepremi di Fine Anno")
    
    try:
        matches_res = supabase.table("match_results").select("*").eq("season", active_season).execute().data
    except:
        matches_res = []
        
    classifica_dict = {t['id']: {"name": t['name'], "pt": 0, "tot_score": 0.0, "giocate": 0} for t in teams}
    
    for m in matches_res:
        t_id = m.get('team_id')
        if t_id in classifica_dict:
            classifica_dict[t_id]["giocate"] += 1
            classifica_dict[t_id]["pt"] += m.get('match_points', 0)
            classifica_dict[t_id]["tot_score"] += float(m.get('team_score', 0))
            
    classifica_ordinata = sorted(classifica_dict.values(), key=lambda x: (x["pt"], x["tot_score"]), reverse=True)
    
    num_squadre = len(teams)
    totale_pool_euro = (num_squadre - 1) * 20.0 if num_squadre > 0 else 0
    premio_1 = totale_pool_euro * 0.70
    premio_2 = totale_pool_euro * 0.30
    premio_3 = 20.0
    
    for idx, item in enumerate(classifica_ordinata):
        if idx == 0:
            item['montepremi_val'] = premio_1
            item['montepremi'] = f"🥇 {premio_1:.2f} € (70%)"
        elif idx == 1:
            item['montepremi_val'] = premio_2
            item['montepremi'] = f"🥈 {premio_2:.2f} € (30%)"
        elif idx == 2:
            item['montepremi_val'] = premio_3
            item['montepremi'] = f"🥉 {premio_3:.2f} € (Rimborso)"
        else:
            item['montepremi_val'] = 0.0
            item['montepremi'] = "0.00 €"

    if classifica_ordinata:
        st.write(f"💵 **Pool Montepremi Totale (Quota 20€ x squadre):** {totale_pool_euro:.2f} €")
        df_rank = pd.DataFrame(classifica_ordinata)
        df_rank.index = range(1, len(df_rank) + 1)
        df_rank.columns = ["Squadra", "Punti", "Punti Totali Giornate", "Partite Giocate", "Valore Premio", "Premio Stimato"]
        df_rank_display = df_rank[["Squadra", "Punti", "Punti Totali Giornate", "Partite Giocate", "Premio Stimato"]]
        st.dataframe(df_rank_display, use_container_width=True)
        st.divider()

    st.header("📈 Proiezione Trimestrale dei Flussi di Cassa")
    st.write("Visualizzazione grafica in tempo reale dell'evoluzione della cassa intera attraverso i 4 trimestri stagionali: **Mese 0** (Attuale) ➔ **Mese 3** (+120 crediti) ➔ **Mese 6** (+120 crediti e -50% stipendi) ➔ **Mese 9** (+120 crediti) ➔ **Mese 12** (+120 crediti, -50% stipendi rimanenti, saldo stadio, luxury tax e paracadute).")
    
    valori_bonus = {'Base': int(rules['bonus_base']), 'Medio': int(rules['bonus_medio']), 'Top': int(rules['bonus_top']), 'Advanced': int(rules['bonus_advanced'])}
    valori_maint = {'Base': int(rules.get('maint_base', 2)), 'Medio': int(rules.get('maint_medio', 5)), 'Top': int(rules.get('maint_top', 10)), 'Advanced': int(rules.get('maint_advanced', 15))}
    
    name_to_id = {t['name']: t['id'] for t in teams}
    classifica_peggiori = sorted(classifica_ordinata, key=lambda x: (x['pt'], x['tot_score'])) if classifica_ordinata else []
    ultimi_tre_ids = [name_to_id[item['name']] for item in classifica_peggiori[:3] if item['name'] in name_to_id]

    proiezioni_table = []
    projection_steps_dict = {}

    for team in teams:
        t_id = team['id']
        t_name = team['name']
        cassa_iniziale = int(round(float(team.get('balance', 500))))
        
        t_players = [p for p in players if p.get('team_id') == t_id and not check_is_abroad(p)]
        tot_stipendi = int(sum([int(round(float(p.get('salary') or 0))) for p in t_players]))
        meta_stipendi = int(round(tot_stipendi * 0.5))
        
        salary_cap = int(round(float(rules.get('salary_cap', 315))))
        sforo = max(0, tot_stipendi - salary_cap)
        luxury_tax = int(round(sforo * 0.5))
        
        t_lvl = team.get('stadium_level', 'Base')
        costo_manutenzione_stadio = int(valori_maint.get(t_lvl, int(rules.get('maint_base', 2))))
        bonus_stadio = int(valori_bonus.get(t_lvl, int(rules['bonus_base'])))
        
        paracadute = 0
        if ultimi_tre_ids:
            if t_id == ultimi_tre_ids[0]:
                paracadute = int(round(float(rules['paracadute_1'])))
            elif len(ultimi_tre_ids) > 1 and t_id == ultimi_tre_ids[1]:
                paracadute = int(round(float(rules['paracadute_2'])))
            elif len(ultimi_tre_ids) > 2 and t_id == ultimi_tre_ids[2]:
                paracadute = int(round(float(rules['paracadute_3'])))

        m0 = cassa_iniziale
        m3 = m0 + 120
        m6 = m3 + 120 - meta_stipendi
        m9 = m6 + 120
        m12 = m9 + 120 - meta_stipendi - costo_manutenzione_stadio + bonus_stadio - luxury_tax + paracadute

        projection_steps_dict[t_name] = [m0, m3, m6, m9, m12]

        proiezioni_table.append({
            "Squadra": t_name,
            "Cassa Attuale (M0)": m0,
            "Mese 3 (+120)": m3,
            "Mese 6 (-50% Stip)": m6,
            "Mese 9 (+120)": m9,
            "Mese 12 (Saldo Finale)": m12,
            "Stipendi Totali": tot_stipendi,
            "Luxury Tax": luxury_tax,
            "Netto Stadio": bonus_stadio - costo_manutenzione_stadio,
            "Paracadute": paracadute
        })

    if projection_steps_dict:
        timeline_index = [
            "00 - Inizio",
            "03 - 1° Trimestre",
            "06 - 2° Trimestre",
            "09 - 3° Trimestre",
            "12 - Fine Anno"
        ]
        df_projection_chart = pd.DataFrame(projection_steps_dict, index=timeline_index)
        st.line_chart(df_projection_chart)
    else:
        st.info("Dati insufficienti per generare il grafico finanziario dinamico.")

    st.subheader("📋 Tabella Dettaglio Flussi Trimestrali & Proiezione di Fine Anno (Interi)")
    df_proj = pd.DataFrame(proiezioni_table)
    st.dataframe(df_proj, use_container_width=True)
    st.divider()

    st.header("Situazione Finanziaria, Salary Cap & Stadi")
    if not teams:
        st.info("Nessuna squadra presente.")
    else:
        SALARY_CAP = int(round(float(rules['salary_cap'])))
        totale_tax_raccolta = 0
        dati_tax = []
        rank_map = {item['name']: idx+1 for idx, item in enumerate(classifica_ordinata)}

        for team in teams:
            t_players = [p for p in players if p.get('team_id') == team['id'] and not check_is_abroad(p)]
            monte_ingaggi = int(sum([int(round(float(p.get('salary') or 0))) for p in t_players]))
            sforo = max(0, monte_ingaggi - SALARY_CAP)
            tassa_dovuta = int(round(sforo * 0.5))
            totale_tax_raccolta += tassa_dovuta
            
            calc_rank = rank_map.get(team['name'], 1)
            dati_tax.append({
                "team_id": team['id'], "name": team['name'], "monte_ingaggi": monte_ingaggi,
                "sforo": sforo, "tassa": tassa_dovuta, "ranking": calc_rank
            })

            col1, col2, col3, col4, col5, col6 = st.columns(6)
            col1.write(f"🛡️ **{team['name']}**")
            col2.markdown(f"💰 Cassa: **{int(round(float(team['balance'])))} M**<br>👶 U21: **{int(round(float(team.get('u21_balance', 30))))} M**", unsafe_allow_html=True)
            col3.write(f"💵 Ingaggi: **{monte_ingaggi}M** / {SALARY_CAP}M")
            if sforo > 0:
                col4.markdown(f"<span style='color: #c0392b; font-weight:bold;'>Sforo: +{sforo}M<br>Tax: -{tassa_dovuta}M</span>", unsafe_allow_html=True)
            else:
                col4.markdown("<span style='color: #27ae60; font-weight:bold;'>In regola 🟢</span>", unsafe_allow_html=True)
            
            s_name = team.get('stadium_name', 'Stadio Comunale')
            s_level = team.get('stadium_level', 'Base')
            col5.markdown(f"🏟️ **{s_name}**<br>({s_level})", unsafe_allow_html=True)
            col6.write(f"📜 Anni Contratto: **{int(team['total_contract_years'])}/{int(rules['max_contract_years'])}**")
            st.divider()

        st.subheader("💡 Simulazione Previsionale Distribuzione a 'Cascade' della Luxury Tax")
        st.write(f"Totale Luxury Tax accumulata dalle squadre oltre il cap: **{totale_tax_raccolta} M**")
        
        virtuose = [d for d in dati_tax if d['sforo'] == 0]
        if virtuose and totale_tax_raccolta > 0:
            virtuose_ordinate = sorted(virtuose, key=lambda x: x['ranking'])
            quota_base = int(round(totale_tax_raccolta / len(virtuose_ordinate)))
            
            st.write("Previsione di distribuzione della tassa tra le squadre virtuose in base al piazzamento in classifica:")
            for v in virtuose_ordinate:
                st.markdown(f"- **{v['name']}** (Rank {v['ranking']}): riceverebbe stimati **+{quota_base} M**")
        else:
            st.info("Nessuna squadra virtuosa o tassa accumulata al momento.")

# TAB NUOVA: MERCATO LIBERO & VARIAZIONI
with tab_free:
    st.header("🔎 Mercato Svincolati e Variazioni di Valore")
    
    with st.expander("📝 Listone Svincolati (Giocatori Senza Squadra)", expanded=True):
        free_agents = [p for p in players if p.get('team_id') is None]
        if not free_agents:
            st.info("Tutti i giocatori sono stati assegnati!")
        else:
            df_fa = pd.DataFrame(free_agents)
            df_fa['Valore'] = df_fa['current_fg_value'].apply(lambda x: int(round(float(x or 1))))
            df_fa_display = df_fa[['name', 'roles', 'serie_a_team', 'Valore']].copy()
            df_fa_display.columns = ["Giocatore", "Ruoli", "Squadra Serie A", "Quotazione"]
            df_fa_display = df_fa_display.sort_values(by="Quotazione", ascending=False).reset_index(drop=True)
            st.dataframe(df_fa_display, use_container_width=True)

    with st.expander("📈 Giocatori con Variazione di Valore (Accasati)"):
        variati = []
        for p in players:
            if p.get('team_id') is not None:
                valore_att = int(round(float(p.get('current_fg_value') or 0)))
                stipendio = int(round(float(p.get('salary') or 0)))
                if valore_att != stipendio:
                    fanta_team = next((t['name'] for t in teams if t['id'] == p['team_id']), "N/D")
                    variazione = valore_att - stipendio
                    segno = "+" if variazione > 0 else ""
                    variati.append({
                        "Giocatore": p['name'],
                        "Valore Attuale": valore_att,
                        "Stipendio": stipendio,
                        "Variazione": f"{segno}{variazione} M",
                        "Squadra Serie A": p.get('serie_a_team', ''),
                        "Fanta Squadra": fanta_team
                    })
        if variati:
            df_var = pd.DataFrame(variati).sort_values(by="Valore Attuale", ascending=False).reset_index(drop=True)
            st.dataframe(df_var, use_container_width=True)
        else:
            st.info("Nessun giocatore ha attualmente un valore di mercato diverso dal proprio stipendio d'acquisto.")

# TAB 3: ROSE ORDINATE PER RUOLO E AZIONI (CON MODIFICA MULTIPLA ADMIN E ACCESSO VISITATORE)
with tab3:
    if st.session_state.is_admin:
        st.header("Gestione Rose & Modifica Massiva (Admin)")
        selected_team_id = st.selectbox("Seleziona Squadra", options=[t['id'] for t in teams], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x), key="select_squadra_rose_admin")
    elif st.session_state.authenticated:
        selected_team_id = st.session_state.team_id
        st.header("La Mia Rosa & Dashboard Preventiva (Lungo Termine)")
    else:
        st.header("Rose delle Squadre")
        selected_team_id = st.selectbox("Seleziona Squadra da ispezionare", options=[t['id'] for t in teams], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x), key="select_squadra_rose_viewer")

    if teams:
        raw_team_players = [p for p in players if p.get('team_id') == selected_team_id]
        team_players = sorted(raw_team_players, key=lambda p: (get_player_role_priority(p.get('roles', '')), p.get('name', '')))
        team_data = next(t for t in teams if t['id'] == selected_team_id)
        
        if not team_players:
            st.info("Nessun giocatore in rosa.")
        else:
            h1, h2, h3, h4, h5, h6 = st.columns([2, 1, 1, 1, 1, 1])
            h1.markdown("**Giocatore**")
            h2.markdown("**Stipendio**")
            h3.markdown("**Q. Attuale**")
            h4.markdown("**Variazione**")
            h5.markdown("**Contratto**")
            if st.session_state.authenticated:
                h6.markdown("**Azioni / Stato**")
            else:
                h6.markdown("**Stato**")
            st.divider()

            updated_players = {}

            for p in team_players:
                col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 1, 1, 1])
                badge_html = render_role_badge(p.get('roles', ''))
                squadra_sa = f" ({p.get('serie_a_team', '')})" if p.get('serie_a_team') else ""
                
                is_abroad_flag = check_is_abroad(p)
                extra_tag = " <span style='color: #e67e22; font-weight: bold;'>[✈️ ESTERO]</span>" if is_abroad_flag else ""
                
                col1.markdown(f"{badge_html} **{p['name']}**{squadra_sa}{extra_tag}", unsafe_allow_html=True)
                
                stipendio_contratto = int(round(float(p.get('salary') or 0)))
                quotazione_attuale = int(round(float(p.get('current_fg_value') or 0)))
                anni_res_p = int(p.get('contract_years') or 0)
                
                fut_sal = p.get('future_salary')
                fut_yr = p.get('future_contract_years')
                
                # Modifica massiva per Admin
                if st.session_state.is_admin:
                    if is_abroad_flag:
                        col2.markdown(f"~~{stipendio_contratto} M~~ <br><small style='color:#e67e22'>Congelato</small>", unsafe_allow_html=True)
                        new_sal = stipendio_contratto
                    else:
                        new_sal = col2.number_input("Sal", min_value=0, value=stipendio_contratto, step=1, key=f"sal_{p['id']}", label_visibility="collapsed")
                    
                    new_yr = col5.number_input("Anni", min_value=0, max_value=5, value=anni_res_p, step=1, key=f"yr_{p['id']}", label_visibility="collapsed")
                    
                    updated_players[p['id']] = {"salary": new_sal, "contract_years": new_yr, "old_salary": stipendio_contratto, "old_years": anni_res_p}
                else:
                    if is_abroad_flag:
                        col2.markdown(f"~~{stipendio_contratto} M~~ <br><small style='color:#e67e22'>Congelato</small>", unsafe_allow_html=True)
                    else:
                        col2.write(f"{stipendio_contratto} M")
                    
                    if anni_res_p <= 1:
                        col5.markdown(f"**{anni_res_p} anni** ‼️")
                    else:
                        col5.write(f"{anni_res_p} anni")
                
                col3.write(f"{quotazione_attuale} M")
                
                differenza = quotazione_attuale - stipendio_contratto
                if differenza > 0:
                    col4.markdown(f"<span style='color: #27ae60; font-weight: bold;'>+{differenza} M 🟢</span>", unsafe_allow_html=True)
                elif differenza < 0:
                    col4.markdown(f"<span style='color: #c0392b; font-weight: bold;'>{differenza} M 🔴</span>", unsafe_allow_html=True)
                else:
                    col4.markdown("<span style='color: #7f8c8d;'>0 M</span>", unsafe_allow_html=True)
                
                if fut_sal and fut_yr:
                    col6.markdown(f"🔄 **Rinnovato:**<br><small>{fut_yr} anni a {fut_sal}M</small>", unsafe_allow_html=True)
                else:
                    # Azioni per Admin o Proprietario
                    if st.session_state.is_admin or (st.session_state.authenticated and selected_team_id == st.session_state.team_id):
                        btn_svincola = col6.button("Svincola ❌", key=f"svincola_{p['id']}")
                        btn_estero = col6.button("Cedi Estero ✈️", key=f"estero_{p['id']}")
                        
                        # Rinnovo (se manca 1 anno)
                        if anni_res_p == 1:
                            with col6.popover("Rinnova 📝"):
                                st.write(f"Rinnovo per {p['name']}")
                                new_fut_sal = st.number_input("Nuovo Stipendio (M)", min_value=1, value=stipendio_contratto, step=1, key=f"rin_sal_{p['id']}")
                                new_fut_yr = st.number_input("Anni Aggiuntivi", min_value=1, max_value=3, value=1, step=1, key=f"rin_yr_{p['id']}")
                                if st.button("Firma Rinnovo", key=f"btn_firma_{p['id']}"):
                                    try:
                                        supabase.table("players").update({"future_salary": new_fut_sal, "future_contract_years": new_fut_yr}).eq("id", p['id']).execute()
                                        t_p_agg = supabase.table("players").select("contract_years, future_contract_years").eq("team_id", selected_team_id).execute().data
                                        tot_y = sum([int(tp.get('contract_years') or 0) + int(tp.get('future_contract_years') or 0) for tp in t_p_agg])
                                        supabase.table("teams").update({"total_contract_years": tot_y}).eq("id", selected_team_id).execute()
                                        st.rerun()
                                    except Exception as e:
                                        pass

                        if btn_svincola:
                            penale = calcola_10_percento(stipendio_contratto)
                            cassa_team_attuale = int(round(float(team_data['balance'])))
                            nuova_cassa = cassa_team_attuale - penale
                            nuovi_anni = int(team_data['total_contract_years']) - int(p.get('contract_years') or 0) - int(p.get('future_contract_years') or 0)
                            
                            if nuova_cassa < 0:
                                st.error(f"Fondi insufficienti per pagare la penale ({penale}M).")
                            else:
                                try:
                                    supabase.table("transfer_history").insert({"player_name": p['name'], "team_id": selected_team_id}).execute()
                                except:
                                    pass
                                    
                                upd_svinc = {"team_id": None, "salary": None, "contract_years": None, "is_under_21": False, "future_salary": None, "future_contract_years": None}
                                try:
                                    supabase.table("players").update({**upd_svinc, "is_abroad": False}).eq("id", p['id']).execute()
                                except:
                                    supabase.table("players").update(upd_svinc).eq("id", p['id']).execute()
                                    
                                supabase.table("teams").update({"balance": int(nuova_cassa), "total_contract_years": int(nuovi_anni)}).eq("id", selected_team_id).execute()
                                registra_snapshot_finanziario(selected_team_id, f"Svincolo {p['name']}", nuova_cassa)
                                st.success(f"{p['name']} svincolato!")
                                st.rerun()
                                
                        if btn_estero:
                            p_price = int(round(float(p.get('purchase_price') or stipendio_contratto)))
                            tot_anni = int(p.get('initial_contract_years') or 3)
                            anni_res = int(p.get('contract_years') or 1)
                            valore_residuo = int(round((p_price / max(1, tot_anni)) * anni_res))
                            
                            cassa_team_attuale = int(round(float(team_data['balance'])))
                            nuova_cassa = cassa_team_attuale + valore_residuo
                            nuovi_anni = int(team_data['total_contract_years']) - int(p.get('contract_years') or 0) - int(p.get('future_contract_years') or 0)
                            
                            try:
                                supabase.table("transfer_history").insert({"player_name": p['name'], "team_id": selected_team_id}).execute()
                            except:
                                pass
                                
                            upd_estero = {"team_id": None, "salary": None, "contract_years": None, "is_under_21": False, "future_salary": None, "future_contract_years": None}
                            try:
                                supabase.table("players").update({**upd_estero, "is_abroad": False}).eq("id", p['id']).execute()
                            except:
                                supabase.table("players").update(upd_estero).eq("id", p['id']).execute()
                                
                            supabase.table("teams").update({"balance": int(nuova_cassa), "total_contract_years": int(nuovi_anni)}).eq("id", selected_team_id).execute()
                            registra_snapshot_finanziario(selected_team_id, f"Cessione Estero {p['name']}", nuova_cassa)
                            st.success(f"✈️ {p['name']} ceduto all'estero! Incassati {valore_residuo}M (valore residuo ammortato).")
                            st.rerun()

            if st.session_state.is_admin and team_players:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💾 Salva Tutte le Modifiche alla Rosa (Stipendi e Anni)", type="primary", use_container_width=True):
                    changes_made = False
                    for pid, data in updated_players.items():
                        if data['salary'] != data['old_salary'] or data['contract_years'] != data['old_years']:
                            supabase.table("players").update({"salary": data['salary'], "contract_years": data['contract_years']}).eq("id", pid).execute()
                            changes_made = True
                    
                    if changes_made:
                        t_players_aggiornati = supabase.table("players").select("contract_years, future_contract_years").eq("team_id", selected_team_id).execute().data
                        reale_somma_anni = sum([int(tp.get('contract_years') or 0) + int(tp.get('future_contract_years') or 0) for tp in t_players_aggiornati])
                        supabase.table("teams").update({"total_contract_years": reale_somma_anni}).eq("id", selected_team_id).execute()
                        st.success("✅ Modifiche multiple salvate con successo!")
                        st.rerun()
                    else:
                        st.info("Nessuna modifica rilevata nei campi della rosa.")

            st.markdown("---")
            st.subheader("🔮 Dashboard Preventiva & Analisi Contrattuale (Prossima Stagione)")
            st.write("Panoramica della rosa in ottica futura, con classi di costo e contratti a lungo termine.")
            
            costo_totale_attuale = int(sum([int(round(float(p.get('salary') or 0))) for p in team_players if not check_is_abroad(p)]))
            giocatori_in_scadenza = [p for p in team_players if int(p.get('contract_years') or 0) <= 1]
            anni_residui_totali = int(sum([(int(p.get('contract_years') or 0) + int(p.get('future_contract_years') or 0)) for p in team_players]))
            
            p_col1, p_col2, p_col3 = st.columns(3)
            p_col1.metric("Monte Ingaggi Attivo", f"{costo_totale_attuale} M")
            p_col2.metric("Giocatori in Scadenza (1 anno) ‼️", len(giocatori_in_scadenza))
            p_col3.metric("Anni Contratto Occupati (Inc. Estero)", f"{anni_residui_totali} / {int(rules['max_contract_years'])}")

# TAB 4: PANCHINA UNDER 21
if st.session_state.authenticated:
    with tab4:
        if st.session_state.is_admin:
            st.header("👶 Gestione Panchina Under 21 (Admin)")
            selected_u21_team_id = st.selectbox("Seleziona Squadra", options=[t['id'] for t in teams], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x), key="select_u21_team_admin")
        else:
            selected_u21_team_id = st.session_state.team_id
            st.header("👶 La Tua Panchina Under 21 (Budget Separato 30M)")

        if teams:
            team_u21_data = next(t for t in teams if t['id'] == selected_u21_team_id)
            current_u21_balance = int(round(float(team_u21_data.get('u21_balance', 30))))
            
            st.write(f"💰 **Budget U21 Residuo:** {current_u21_balance} M / 30 M")
            
            squad_u21 = [u for u in u21_players if u.get('team_id') == selected_u21_team_id]
            
            if squad_u21:
                st.write("**Rosa Under 21 Attuale:**")
                u_cols1, u_cols2, u_cols3, u_cols4, u_cols5 = st.columns([2, 1, 1, 1, 1])
                u_cols1.markdown("**Giovane**")
                u_cols2.markdown("**Ruolo**")
                u_cols3.markdown("**Costo U21**")
                u_cols4.markdown("**Presenze/Convocazioni**")
                u_cols5.markdown("**Azione**")
                st.divider()
                
                for g in squad_u21:
                    col_u1, col_u2, col_u3, col_u4, col_u5 = st.columns([2, 1, 1, 1, 1])
                    col_u1.markdown(f"👶 **{g['name']}** ({g.get('serie_a_team', '')})")
                    col_u2.markdown(render_role_badge(g.get('roles', '')), unsafe_allow_html=True)
                    col_u3.write(f"{int(round(float(g.get('budget_used') or 0)))} M")
                    
                    presenze = int(g.get('presenze') or 0)
                    stato_presenze = f"🔥 {presenze} / 5" if presenze < 5 else f"✅ {presenze} / 5 (Obbligo Contratto Raggiunto!)"
                    col_u4.write(stato_presenze)
                    
                    if st.session_state.is_admin:
                        if col_u5.button("Svincola U21 ❌", key=f"svincola_u21_{g['id']}"):
                            refund = int(round(float(g.get('budget_used') or 0)))
                            supabase.table("teams").update({"u21_balance": current_u21_balance + refund}).eq("id", selected_u21_team_id).execute()
                            supabase.table("u21_players").delete().eq("id", g['id']).execute()
                            st.success(f"{g['name']} svincolato dalla U21!")
                            st.rerun()
                    else:
                        col_u5.write("Gestito da Admin")
            else:
                st.info("Nessun giovane Under 21 tesserato in questa panchina.")
                
            if st.session_state.is_admin:
                st.markdown("---")
                st.subheader("➕ Ingaggia Giovane in Panchina U21 (Admin)")
                svincolati_listone = [p for p in players if p.get('team_id') is None]
                
                if svincolati_listone:
                    with st.form("acquista_u21_form"):
                        svincolati_ordinati = sorted(svincolati_listone, key=lambda x: x['name'])
                        selected_u21_player = st.selectbox(
                            "Seleziona Giovane dal Listone Svincolati",
                            options=[p['id'] for p in svincolati_ordinati],
                            format_func=lambda x: next(f"{p['name']} | Ruolo: {p.get('roles', 'N/D')} | Squadra: {p.get('serie_a_team', 'N/D')}" for p in svincolati_ordinati if p['id'] == x)
                        )
                        costo_u21 = st.number_input("Costo d'Acquisto dal Budget U21 (M)", min_value=1, max_value=int(max(1, current_u21_balance)), value=1, step=1)
                        
                        if st.form_submit_button("Aggiungi alla Panchina U21 ✍️"):
                            p_obj = next(p for p in svincolati_listone if p['id'] == selected_u21_player)
                            
                            if current_u21_balance < costo_u21:
                                st.error("❌ Budget U21 insufficiente (massimo 30M totali).")
                            else:
                                supabase.table("u21_players").insert({
                                    "name": p_obj['name'],
                                    "roles": p_obj.get('roles', ''),
                                    "serie_a_team": p_obj.get('serie_a_team', ''),
                                    "team_id": selected_u21_team_id,
                                    "budget_used": int(costo_u21),
                                    "presenze": 0
                                }).execute()
                                
                                supabase.table("teams").update({
                                    "u21_balance": int(current_u21_balance - costo_u21)
                                }).eq("id", selected_u21_team_id).execute()
                                
                                supabase.table("players").update({"team_id": selected_u21_team_id, "salary": 0, "contract_years": 0, "is_under_21": True}).eq("id", selected_u21_player).execute()
                                
                                st.success(f"✅ {p_obj['name']} inserito con successo nella Panchina U21!")
                                st.rerun()

# TAB 5: SCAMBI & PRESTITI
if st.session_state.authenticated:
    with tab5:
        st.header("🤝 Mercato Avanzato: Scambi & Prestiti")
        
        if not teams:
            st.warning("Nessuna squadra presente.")
        else:
            if st.session_state.is_admin:
                user_team_id = st.selectbox(
                    "Seleziona la tua squadra (Sei Admin)", 
                    options=[t['id'] for t in teams], 
                    format_func=lambda x: next(t['name'] for t in teams if t['id'] == x), 
                    key="admin_trade_sender"
                )
            else:
                user_team_id = st.session_state.team_id
            
            tab_scambio, tab_prestito, tab_storico_scambi = st.tabs(["🔄 Proponi Scambio Diretto", "📋 Gestione Prestiti", "📨 Richieste Scambio Ricevute"])
            
            with tab_scambio:
                st.write("Crea una proposta di scambio con un'altra squadra. *Nota: Il differenziale delle quotazioni Mantra tra i giocatori scambiati non deve superare il 10%, altrimenti va colmato con un conguaglio in crediti interi.*")
                
                ricevente_id = st.selectbox("Squadra Destinataria", options=[t['id'] for t in teams if t['id'] != user_team_id], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x), key="sel_ricevente_scambio")
                
                with st.form("proponi_scambio_form"):
                    miei_giocatori = [p for p in players if p.get('team_id') == user_team_id]
                    miei_offerti = st.multiselect("Seleziona tuoi giocatori da OFFRIRE", options=miei_giocatori, format_func=lambda x: f"{x['name']} (Q: {int(round(float(x.get('current_fg_value') or 1)))}M)")
                    
                    giocatori_altra = [p for p in players if p.get('team_id') == ricevente_id]
                    loro_richiesti = st.multiselect("Seleziona giocatori da RICHIEDERE", options=giocatori_altra, format_func=lambda x: f"{x['name']} (Q: {int(round(float(x.get('current_fg_value') or 1)))}M)")
                    
                    conguaglio = st.number_input("Conguaglio in Crediti Interi (positivo se paghi tu, negativo se ricevi)", value=0, step=1)
                    
                    if st.form_submit_button("Invia Proposta di Scambio 🤝"):
                        if not miei_offerti or not loro_richiesti:
                            st.error("Seleziona almeno un giocatore da offrire e uno da richiedere.")
                        else:
                            valore_offerto = sum([int(round(float(p.get('current_fg_value') or 1))) for p in miei_offerti]) + int(conguaglio)
                            valore_richiesto = sum([int(round(float(p.get('current_fg_value') or 1))) for p in loro_richiesti])
                            
                            differenza = abs(valore_offerto - valore_richiesto)
                            tolleranza = max(valore_offerto, valore_richiesto) * 0.10
                            
                            if differenza > tolleranza:
                                st.error(f"❌ Scambio non valido: il differenziale di valore supera il 10% consentito (Delta: {differenza}M, Max tollerato: {int(round(tolleranza))}M). Aggiusta il conguaglio!")
                            else:
                                offerti_str = ",".join([str(p['id']) for p in miei_offerti])
                                richiesti_str = ",".join([str(p['id']) for p in loro_richiesti])
                                try:
                                    supabase.table("trades").insert({
                                        "sender_team_id": user_team_id,
                                        "receiver_team_id": ricevente_id,
                                        "offered_player_ids": offerti_str,
                                        "requested_player_ids": richiesti_str,
                                        "cash_adjustment": int(conguaglio),
                                        "status": "In Attesa",
                                        "season": active_season
                                    }).execute()
                                    st.success("✅ Proposta di scambio inviata con successo!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"⚠️ Errore durante l'invio della proposta di scambio.")
                                    st.info("💡 Assicurati che la tabella 'trades' esista e non abbia blocchi RLS. Vai nell'SQL Editor di Supabase ed esegui:\n`ALTER TABLE public.trades DISABLE ROW LEVEL SECURITY;`")

            with tab_prestito:
                st.write("Gestisci i prestiti dei giocatori (con divisione dello stipendio e blocco dello svincolo unilaterale).")
                
                proprietario_id = st.selectbox("Squadra Proprietaria del Cartellino", options=[t['id'] for t in teams], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x), key="sel_proprietario_prestito")
                giocatori_prop = [p for p in players if p.get('team_id') == proprietario_id]
                
                with st.form("registra_prestito_form"):
                    if giocatori_prop:
                        giocatore_prestito_id = st.selectbox("Giocatore in Prestito", options=[p['id'] for p in giocatori_prop], format_func=lambda x: next(f"{p['name']} (Stipendio: {int(round(float(p.get('salary') or 0)))}M)" for p in giocatori_prop if p['id'] == x), key="sel_gioc_prestito")
                        destinatario_prestito_id = st.selectbox("Squadra Prestataria (Chi riceve)", options=[t['id'] for t in teams if t['id'] != proprietario_id], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x), key="sel_dest_prestito")
                        perc_stipendio = st.slider("Percentuale di stipendio pagata dalla squadra in prestito (%)", min_value=0, max_value=100, value=100, step=10, key="slider_perc_prestito")
                        
                        if st.form_submit_button("Formalizza Prestito 📋"):
                            try:
                                supabase.table("loans").insert({
                                    "player_id": giocatore_prestito_id,
                                    "owner_team_id": proprietario_id,
                                    "borrower_team_id": destinatario_prestito_id,
                                    "salary_percentage_borrower": int(perc_stipendio),
                                    "season": active_season
                                }).execute()
                                supabase.table("players").update({"team_id": destinatario_prestito_id}).eq("id", giocatore_prestito_id).execute()
                                st.success("✅ Contratto di prestito registrato! Il giocatore è stato trasferito temporaneamente e protetto da svincolo unilaterale.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"⚠️ Errore di connessione al database durante la registrazione del prestito.")
                                st.info("💡 Assicurati che la tabella 'loans' esista e non abbia blocchi RLS. Vai nell'SQL Editor di Supabase ed esegui:\n`ALTER TABLE public.loans DISABLE ROW LEVEL SECURITY;`")
                    else:
                        st.info("La squadra selezionata non ha giocatori in rosa.")
                        st.form_submit_button("Formalizza Prestito 📋", disabled=True)
                        
                st.write("**Prestiti Attivi:**")
                if loans_res:
                    for l in loans_res:
                        p_obj = next((p for p in players if p['id'] == l['player_id']), None)
                        owner_obj = next((t for t in teams if t['id'] == l['owner_team_id']), None)
                        borrower_obj = next((t for t in teams if t['id'] == l['borrower_team_id']), None)
                        if p_obj and owner_obj and borrower_obj:
                            col_l1, col_l2 = st.columns([5, 1])
                            col_l1.markdown(f"- 📋 **{p_obj['name']}** (Proprietario: {owner_obj['name']} ➔ In prestito a: {borrower_obj['name']} | Stipendio a carico: {l['salary_percentage_borrower']}%)")
                            
                            if st.session_state.is_admin:
                                if col_l2.button("Revoca ❌", key=f"rev_loan_{l['id']}"):
                                    supabase.table("players").update({"team_id": owner_obj['id']}).eq("id", p_obj['id']).execute()
                                    supabase.table("loans").delete().eq("id", l['id']).execute()
                                    
                                    for team_ricalc_id in [owner_obj['id'], borrower_obj['id']]:
                                        t_p_agg = supabase.table("players").select("contract_years, future_contract_years").eq("team_id", team_ricalc_id).execute().data
                                        tot_y = sum([int(tp.get('contract_years') or 0) + int(tp.get('future_contract_years') or 0) for tp in t_p_agg])
                                        supabase.table("teams").update({"total_contract_years": tot_y}).eq("id", team_ricalc_id).execute()
                                        
                                    st.success(f"Prestito di {p_obj['name']} revocato con successo!")
                                    st.rerun()
                else:
                    st.info("Nessun prestito attivo registrato.")

            with tab_storico_scambi:
                st.write("Proposte di scambio ricevute:")
                mie_proposte = [t for t in trades_res if t['receiver_team_id'] == user_team_id and t['status'] == 'In Attesa']
                
                if mie_proposte:
                    for tr in mie_proposte:
                        sender_obj = next((t for t in teams if t['id'] == tr['sender_team_id']), None)
                        st.write(f"Proposta da parte di **{sender_obj['name'] if sender_obj else 'Altra Squadra'}** | Conguaglio: {int(round(float(tr.get('cash_adjustment') or 0)))}M")
                        
                        col_acc, col_rif = st.columns(2)
                        if col_acc.button("Accetta Scambio ✅", key=f"acc_{tr['id']}"):
                            offerti_ids = [int(i) for i in tr['offered_player_ids'].split(',') if i]
                            richiesti_ids = [int(i) for i in tr['requested_player_ids'].split(',') if i]
                            
                            for pid in offerti_ids:
                                supabase.table("players").update({"team_id": tr['receiver_team_id']}).eq("id", pid).execute()
                            for pid in richiesti_ids:
                                supabase.table("players").update({"team_id": tr['sender_team_id']}).eq("id", pid).execute()
                                
                            supabase.table("trades").update({"status": "Accettato"}).eq("id", tr['id']).execute()
                            st.success("Scambio accettato e completato con successo!")
                            st.rerun()
                            
                        if col_rif.button("Rifiuta ❌", key=f"rif_{tr['id']}"):
                            supabase.table("trades").update({"status": "Rifiutato"}).eq("id", tr['id']).execute()
                            st.warning("Scambio rifiutato.")
                            st.rerun()
                else:
                    st.info("Nessuna proposta di scambio in attesa.")

# TAB 6: INSERIMENTO GIORNATE, CONVOCAZIONI U21 E RITARDO FORMAZIONE
if st.session_state.authenticated:
    with tab6:
        st.header("⚽ Inserimento Risultati Giornata & Convocazioni Under 21")
        st.write("Inserisci i punteggi totali: i gol vengono assegnati partendo da 66 punti (+1 gol ogni 4 punti, es. 66-69.5 = 1 gol, 70-73.5 = 2 gol, 74-77.5 = 3 gol). I punti classifica vengono calcolati in base ai gol.")
        
        if not teams:
            st.warning("Crea prima delle squadre.")
        else:
            with st.form("match_and_u21_form"):
                giornata = st.number_input("Numero Giornata", min_value=1, max_value=38, step=1, value=1)
                
                col_m1, col_m2 = st.columns(2)
                
                team_casa_id = col_m1.selectbox("Squadra Casa", options=[t['id'] for t in teams], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x), key="ins_casa")
                score_casa = col_m1.number_input("Punteggio Totale Casa (es. 74.5)", value=66.0, step=0.5, key="score_c")
                ritardo_casa = col_m1.checkbox("⚠️ Formazione caricata in ritardo? (Multa automatica di 5M interi)", key="rit_c")
                
                col_m1.markdown("---")
                col_m1.markdown("**Convocati Under 21 (Casa):**")
                u21_casa_squad = [u for u in u21_players if u.get('team_id') == team_casa_id]
                convocati_casa_ids = []
                convocati_casa_nomi = []
                if u21_casa_squad:
                    for u_p in u21_casa_squad:
                        if col_m1.checkbox(f"{u_p['name']} ({u_p.get('roles', '')})", key=f"u21_c_{u_p['id']}"):
                            convocati_casa_ids.append(u_p['id'])
                            convocati_casa_nomi.append(u_p['name'])
                else:
                    col_m1.info("Nessun giovane U21 in panchina per questa squadra.")

                team_fuori_id = col_m2.selectbox("Squadra Ospite", options=[t['id'] for t in teams], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x), key="ins_fuori")
                score_fuori = col_m2.number_input("Punteggio Totale Ospite (es. 71.0)", value=66.0, step=0.5, key="score_f")
                ritardo_fuori = col_m2.checkbox("⚠️ Formazione caricata in ritardo? (Multa automatica di 5M interi)", key="rit_f")
                
                col_m2.markdown("---")
                col_m2.markdown("**Convocati Under 21 (Ospite):**")
                u21_fuori_squad = [u for u in u21_players if u.get('team_id') == team_fuori_id]
                convocati_fuori_ids = []
                convocati_fuori_nomi = []
                if u21_fuori_squad:
                    for u_p in u21_fuori_squad:
                        if col_m2.checkbox(f"{u_p['name']} ({u_p.get('roles', '')})", key=f"u21_f_{u_p['id']}"):
                            convocati_fuori_ids.append(u_p['id'])
                            convocati_fuori_nomi.append(u_p['name'])
                else:
                    col_m2.info("Nessun giovane U21 in panchina per questa squadra.")

                if st.form_submit_button("Registra Risultato, Multe & Presenze U21 ⚽"):
                    if team_casa_id == team_fuori_id:
                        st.error("Seleziona due squadre diverse.")
                    else:
                        gol_casa = calcola_gol(score_casa)
                        gol_fuori = calcola_gol(score_fuori)
                        
                        if gol_casa > gol_fuori:
                            pts_casa = 3
                            pts_fuori = 0
                        elif gol_casa == gol_fuori:
                            pts_casa = 1
                            pts_fuori = 1
                        else:
                            pts_casa = 0
                            pts_fuori = 3
                            
                        supabase.table("match_results").insert([
                            {
                                "matchday": int(giornata),
                                "team_id": team_casa_id,
                                "opponent_team_id": team_fuori_id,
                                "team_score": score_casa,
                                "opponent_score": score_fuori,
                                "match_points": pts_casa,
                                "u21_convocati": ", ".join(convocati_casa_nomi),
                                "season": active_season
                            },
                            {
                                "matchday": int(giornata),
                                "team_id": team_fuori_id,
                                "opponent_team_id": team_casa_id,
                                "team_score": score_fuori,
                                "opponent_score": score_casa,
                                "match_points": pts_fuori,
                                "u21_convocati": ", ".join(convocati_fuori_nomi),
                                "season": active_season
                            }
                        ]).execute()
                        
                        multa_valore = 5
                        if ritardo_casa:
                            team_c_obj = next(t for t in teams if t['id'] == team_casa_id)
                            nuova_cassa_c = int(round(float(team_c_obj['balance']))) - multa_valore
                            supabase.table("teams").update({"balance": int(nuova_cassa_c)}).eq("id", team_casa_id).execute()
                            supabase.table("line_up_delays").insert({"team_id": team_casa_id, "matchday": int(giornata), "fine_amount": multa_valore, "season": active_season}).execute()
                            registra_snapshot_finanziario(team_casa_id, f"Multa Ritardo G. {giornata}", nuova_cassa_c)
                            
                        if ritardo_fuori:
                            team_f_obj = next(t for t in teams if t['id'] == team_fuori_id)
                            nuova_cassa_f = int(round(float(team_f_obj['balance']))) - multa_valore
                            supabase.table("teams").update({"balance": int(nuova_cassa_f)}).eq("id", team_fuori_id).execute()
                            supabase.table("line_up_delays").insert({"team_id": team_fuori_id, "matchday": int(giornata), "fine_amount": multa_valore, "season": active_season}).execute()
                            registra_snapshot_finanziario(team_fuori_id, f"Multa Ritardo G. {giornata}", nuova_cassa_f)
                        
                        for uid in convocati_casa_ids:
                            giovane_obj = next((x for x in u21_players if x['id'] == uid), None)
                            if giovane_obj:
                                nuove_presenze = int(giovane_obj.get('presenze') or 0) + 1
                                supabase.table("u21_players").update({"presenze": nuove_presenze}).eq("id", uid).execute()
                                
                        for uid in convocati_fuori_ids:
                            giovane_obj = next((x for x in u21_players if x['id'] == uid), None)
                            if giovane_obj:
                                nuove_presenze = int(giovane_obj.get('presenze') or 0) + 1
                                supabase.table("u21_players").update({"presenze": nuove_presenze}).eq("id", uid).execute()

                        st.success(f"✅ Risultato Giornata {giornata} registrato: **{gol_casa} - {gol_fuori}** ({score_casa} - {score_fuori})! Assegnati {pts_casa} pt alla squadra di casa e {pts_fuori} pt all'ospite.")
                        st.rerun()

# TAB 7: MERCATO ADMIN (Se Admin)
if st.session_state.is_admin:
    with tab7:
        st.header("Mercato Svincolati & Scadenze di Febbraio (Admin)")
        
        tab_mercato_normale, tab_aste_febbraio = st.tabs(["Listone Svincolati", "🔥 Aste Contratti in Scadenza (Febbraio)"])
        
        with tab_mercato_normale:
            svincolati = [p for p in players if p.get('team_id') is None]
            
            if not svincolati:
                st.warning("⚠️ Il listone è vuoto!")
            elif teams:
                col1, col2 = st.columns(2)
                with col1:
                    team_id = st.selectbox("Acquirente", options=[t['id'] for t in teams], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x), key="acq_team_mercato")
                    
                    svincolati_ordinati = sorted(svincolati, key=lambda x: x['name'])
                    selected_player_id = st.selectbox(
                        "Cerca e Seleziona Giocatore dal Listone", 
                        options=[p['id'] for p in svincolati_ordinati], 
                        format_func=lambda x: next(f"{p['name']} | Ruolo: {p.get('roles', 'N/D')} | Squadra: {p.get('serie_a_team', 'N/D')} | Quotazione: {int(round(float(p.get('current_fg_value') or 1)))} M" for p in svincolati_ordinati if p['id'] == x),
                        key="acq_player_mercato"
                    )
                    
                with col2:
                    player_obj_preview = next((p for p in svincolati if p['id'] == selected_player_id), None)
                    stipendio_fisso = int(round(float(player_obj_preview.get('current_fg_value') or 1))) if player_obj_preview else 1
                    
                    st.write(f"💵 **Stipendio (Quotazione):** {stipendio_fisso} M")
                    prezzo_acquisto = st.number_input("Prezzo d'Acquisto Reale (M)", min_value=1, value=int(stipendio_fisso), step=1, key=f"acq_price_{selected_player_id}")
                    anni_contratto = st.number_input("Anni di Contratto", min_value=1, max_value=3, step=1, key=f"acq_years_{selected_player_id}")
                    
                if st.button("Firma Contratto & Paga Cartellino ✍️", key=f"btn_buy_{selected_player_id}"):
                    player_obj = next(p for p in svincolati if p['id'] == selected_player_id)
                    nome_giocatore = player_obj['name']
                    
                    try:
                        hist_check = supabase.table("transfer_history").select("*").eq("team_id", team_id).eq("player_name", nome_giocatore).execute().data
                        bloccato = False
                        if hist_check:
                            vendita_dt = datetime.fromisoformat(hist_check[0]['sale_date'].replace('Z', '+00:00'))
                            if (datetime.now(vendita_dt.tzinfo) - vendita_dt).days < 365:
                                bloccato = True
                    except:
                        bloccato = False
                        
                    if bloccato:
                        st.error("❌ Impossibile riacquistare questo giocatore: è stato ceduto da meno di 12 mesi (Regolamento Blocco Riacquisto).")
                    else:
                        stipendio = int(stipendio_fisso)
                        bonus_firma = calcola_10_percento(stipendio)
                        costo_totale_iniziale = int(prezzo_acquisto) + bonus_firma
                        t_data = next(t for t in teams if t['id'] == team_id)
                        cassa_t = int(round(float(t_data['balance'])))
                        
                        if cassa_t < costo_totale_iniziale:
                            st.error(f"❌ Fondi insufficienti in cassa! (Richiesti: {costo_totale_iniziale}M tra prezzo d'acquisto e bonus firma)")
                        elif (int(t_data['total_contract_years']) + anni_contratto) > int(rules['max_contract_years']):
                            st.error(f"❌ Limite di {int(rules['max_contract_years'])} anni di contratto superato!")
                        else:
                            upd_acq = {
                                "team_id": team_id,
                                "salary": int(stipendio),
                                "contract_years": int(anni_contratto),
                                "purchase_price": int(prezzo_acquisto),
                                "initial_contract_years": int(anni_contratto)
                            }
                            try:
                                supabase.table("players").update({**upd_acq, "is_abroad": False}).eq("id", selected_player_id).execute()
                            except:
                                supabase.table("players").update(upd_acq).eq("id", selected_player_id).execute()
                            
                            new_balance = cassa_t - costo_totale_iniziale
                            
                            t_p_agg = supabase.table("players").select("contract_years, future_contract_years").eq("team_id", team_id).execute().data
                            tot_y = sum([int(tp.get('contract_years') or 0) + int(tp.get('future_contract_years') or 0) for tp in t_p_agg])

                            supabase.table("teams").update({
                                "balance": int(new_balance),
                                "total_contract_years": tot_y
                            }).eq("id", team_id).execute()
                            
                            registra_snapshot_finanziario(team_id, f"Acquisto {nome_giocatore} (Cartellino + Bonus)", new_balance)
                            st.success(f"✅ {nome_giocatore} acquistato con successo! Scalati {prezzo_acquisto}M di cartellino e {bonus_firma}M di bonus firma dalla cassa.")
                            st.rerun()

        with tab_aste_febbraio:
            st.write("🔥 Gestione giocatori in scadenza dal 1° febbraio con asta al rialzo basata sullo stipendio.")
            scadenti = [p for p in players if int(p.get('contract_years') or 0) == 1 and p.get('team_id') is not None]
            if scadenti:
                for s in scadenti:
                    t_prop = next((t['name'] for t in teams if t['id'] == s['team_id']), "Altra Squadra")
                    st.markdown(f"- **{s['name']}** (Proprietario: {t_prop} | Stipendio attuale: {int(round(float(s.get('salary') or 0)))}M)")
            else:
                st.info("Nessun giocatore in scadenza di contratto al momento.")

# TAB REPORT: ATTIVITA' E LOG
with tab_report:
    st.header("📜 Report Attività e Modifiche")
    st.write("In questa schermata puoi monitorare gli ultimi aggiornamenti effettuati sulle casse delle squadre (es. Svincoli, Multe, Tranches, Bonus, Acquisti, Modifiche Admin).")
    
    if fin_history_res:
        df_rep = pd.DataFrame(fin_history_res)
        id_to_name = {t['id']: t['name'] for t in teams}
        df_rep['Fanta Squadra'] = df_rep['team_id'].map(id_to_name)
        
        def format_date(iso_str):
            try:
                dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
                return dt.strftime("%d/%m/%Y %H:%M:%S")
            except:
                return iso_str
        
        if 'timestamp' in df_rep.columns:
            df_rep['Data e Ora'] = df_rep['timestamp'].apply(format_date)
            df_rep = df_rep.sort_values(by='timestamp', ascending=False)
        else:
            df_rep['Data e Ora'] = "N/D"
            
        df_rep['Azione / Modifica'] = df_rep['event_label']
        df_rep['Nuovo Saldo (M)'] = df_rep['balance_snapshot']
        
        df_rep_display = df_rep[['Data e Ora', 'Fanta Squadra', 'Azione / Modifica', 'Nuovo Saldo (M)']].reset_index(drop=True)
        st.dataframe(df_rep_display, use_container_width=True)
    else:
        st.info("Nessuna attività registrata finora nell'ambiente finanziario.")

# TAB ALBO D'ORO: CONSULTAZIONE STAGIONI ARCHIVIATE
with tab_hof:
    st.header("🏛️ Albo d'Oro & Archivio Storico Campionati")
    st.write("Consulta le classifiche ufficiali e i risultati di tutte le partite delle stagioni passate:")
    
    try:
        hof_res = supabase.table("hall_of_fame_seasons").select("*").order("season", desc=True).execute().data
    except:
        hof_res = []
        
    if not hof_res:
        st.info("Nessuna stagione ancora archiviata nell'Albo d'Oro. La prima stagione verrà archiviata al completamento della Procedura di Fine Stagione.")
    else:
        stagioni_disponibili = [h['season'] for h in hof_res if 'season' in h]
        if not stagioni_disponibili:
            st.info("Nessuna stagione trovata.")
        else:
            stagione_scelta = st.selectbox("Seleziona la Stagione da Consultare:", options=stagioni_disponibili, key="hof_season_select")
            
            dati_archivio = next((h for h in hof_res if h.get('season') == stagione_scelta), None)
            
            if dati_archivio:
                st.markdown(f"### 🏆 Classifica Finale Ufficiale - Stagione {stagione_scelta}")
                final_standings = dati_archivio.get('final_standings') or []
                if final_standings:
                    df_hof_rank = pd.DataFrame(final_standings)
                    df_hof_rank.index = range(1, len(df_hof_rank) + 1)
                    
                    cols_to_show = [c for c in ["name", "pt", "tot_score", "giocate", "montepremi"] if c in df_hof_rank.columns]
                    df_hof_display = df_hof_rank[cols_to_show].copy()
                    rename_map = {"name": "Squadra", "pt": "Punti", "tot_score": "Totale Punti", "giocate": "Partite", "montepremi": "Premio"}
                    df_hof_display.rename(columns=rename_map, inplace=True)
                    st.dataframe(df_hof_display, use_container_width=True)
                else:
                    st.info("Dati della classifica finale non disponibili per questa stagione.")
                    
                st.markdown("---")
                st.markdown("### ⚽ Dettaglio Risultati Giornate")
                storico_match = dati_archivio.get('match_results') or []
                if storico_match:
                    matchdays = sorted(list(set([m['matchday'] for m in storico_match if 'matchday' in m])))
                    if matchdays:
                        giornata_sel = st.selectbox("Seleziona Giornata da visualizzare:", options=matchdays, key="hof_giornata_select")
                        matches_giornata = [m for m in storico_match if m.get('matchday') == giornata_sel]
                        
                        for i in range(0, len(matches_giornata), 2):
                            m_a = matches_giornata[i]
                            m_b = matches_giornata[i+1] if i+1 < len(matches_giornata) else None
                            if m_b:
                                team_a_name = next((t['name'] for t in teams if t['id'] == m_a.get('team_id')), f"Team {m_a.get('team_id')}")
                                team_b_name = next((t['name'] for t in teams if t['id'] == m_b.get('team_id')), f"Team {m_b.get('team_id')}")
                                score_a = m_a.get('team_score', 0)
                                score_b = m_b.get('team_score', 0)
                                gol_a = calcola_gol(score_a)
                                gol_b = calcola_gol(score_b)
                                
                                col_h1, col_h2, col_h3 = st.columns([2, 1, 2])
                                col_h1.write(f"🏠 **{team_a_name}** ({score_a} pt)")
                                col_h2.markdown(f"<h4 style='text-align: center; margin: 0;'>{gol_a} - {gol_b}</h4>", unsafe_allow_html=True)
                                col_h3.write(f"✈️ **{team_b_name}** ({score_b} pt)")
                    else:
                        st.info("Nessuna giornata presente nei dati archiviati.")
                else:
                    st.info("Nessun match registrato per questa stagione.")

# TAB REGOLAMENTO
with tab_reg:
    st.header("📖 Regolamento Ufficiale FantaGestionale")
    st.write("Benvenuti nel cuore pulsante della lega. Questo regolamento disciplina gli aspetti economici e contrattuali per garantire un bilanciamento manageriale duraturo nel tempo.")
    
    st.markdown("""
    ### 1. Finanze e Flussi di Cassa
    Ogni squadra inizia la sua storia con un budget base di **500 Crediti**. 
    Il campionato è diviso in 4 trimestri economici. All'inizio del 1°, del 2°, del 3° e del 4° trimestre viene erogata una **Tranche di 120 Crediti**.
    Gli stipendi dei giocatori pesano sul bilancio: **il 50% del totale del monte ingaggi viene pagato al 2° Trimestre, il restante 50% viene pagato a fine anno**.

    ### 2. Contratti, Salary Cap e Luxury Tax
    Ogni lega deve rispettare dei paletti per non fallire:
    * **Limite Anni:** La somma degli anni di contratto di tutti i giocatori in rosa non può superare il limite di **55 Anni**. Un giocatore può firmare per un massimo di 3 anni alla volta.
    * **Salary Cap (Tetto Ingaggi):** Fissato a **315 M**.
    * **Luxury Tax:** Superare il Salary Cap è permesso, ma costa caro. Chi sfora paga una tassa pari al **50% dello sforo**. L'intero ammontare della Luxury Tax raccolta a fine anno viene diviso in parti uguali e ridistribuito come premio di rendimento alle squadre virtuose che NON hanno sforato il tetto.

    ### 3. Svincoli, Penali e Rinnovi
    * **Svincolo Unilaterale:** Svincolare un giocatore comporta il pagamento di una penale immediata pari al **10% del suo stipendio** (arrotondato).
    * **Rinnovi:** I giocatori in scadenza (1 anno rimasto) possono essere rinnovati. Verrà concordato un "Nuovo Stipendio" e degli "Anni Aggiuntivi". Gli anni extra si sommano *immediatamente* al calcolo dei 55 anni limite della squadra. Tuttavia, lo stipendio attuale rimarrà in vigore per la stagione in corso, e il nuovo stipendio si attiverà in automatico solo alla fine dell'anno, evitando lo svincolo.

    ### 4. Cessioni all'Estero
    Se un giocatore va all'estero nella realtà, la FantaSquadra incassa immediatamente il **valore residuo ammortizzato** del cartellino. *Alternativamente*, è possibile mantenere il giocatore in rosa come "Congelato": i suoi anni di contratto continuano a pesare sul totale della squadra, ma **il suo stipendio non viene contato** né nel Salary Cap né nei pagamenti semestrali. Se torna in Serie A, il contratto si scongela.

    ### 5. Infrastrutture: Lo Stadio
    Lo Stadio è un asset fondamentale che garantisce introiti a fine stagione, ma richiede manutenzione. Esistono 4 Livelli:
    1. **Base:** Manutenzione 2M / Bonus Incasso +5M
    2. **Medio:** Manutenzione 5M / Bonus Incasso +10M
    3. **Top:** Manutenzione 10M / Bonus Incasso +15M
    4. **Advanced:** Manutenzione 15M / Bonus Incasso +20M
    *A fine anno viene accreditato in cassa il Saldo Netto (Bonus - Manutenzione). Se una squadra non ha fondi per pagare la manutenzione, lo stadio viene **declassato** al livello inferiore.*

    ### 6. Settore Giovanile (Panchina U21)
    Esiste una cassa parallela, separata da quella principale, dedicata ai giovani: **Budget U21 di 30M**.
    In questa panchina possono essere tesserati solo giocatori giovani presi dal listone. 
    Per poterli promuovere a tutti gli effetti come futuri titolari, il giovane **deve accumulare 5 presenze** (convocazioni a voto) durante la stagione. Svincolare un U21 rimborsa per intero il suo costo sul Budget U21.

    ### 7. Partite, Gol e Multe
    Il calcolo dei gol segue fasce matematiche rigorose:
    * Meno di **66 punti** = 0 Gol.
    * Da **66 punti** = 1 Gol.
    * Ogni **4 punti successivi** = +1 Gol (es. 70=2, 74=3, 78=4, ecc.).
    * **Multa Ritardo:** Se la formazione viene schierata in ritardo, scatta automaticamente una multa disciplinare di **5 M** sottratta dalla cassa societaria.

    ### 8. Scambi e Prestiti
    Il mercato tra presidenti è libero ma sorvegliato:
    * **Scambi Definitivi:** Il differenziale delle quotazioni tra i giocatori scambiati non deve superare il 10%. Se lo supera, va obbligatoriamente compensato inserendo un "Conguaglio in Crediti".
    * **Prestiti:** I giocatori possono essere prestati ad altre squadre. Si può decidere con un cursore (da 0% a 100%) quanta percentuale dello stipendio verrà pagata da chi riceve il prestito a fine anno.

    ### 9. Premi e Paracadute di Fine Stagione
    A fine anno, dopo la 38° giornata, la cassa comune (costituita dalle quote di partecipazione) viene distribuita:
    * **1° Classificato:** 70% del montepremi.
    * **2° Classificato:** 30% del montepremi.
    * **3° Classificato:** Rimborso quota d'iscrizione.
    * **Paracadute:** Per bilanciare la lega, le ultime tre squadre classificate ricevono un'iniezione di cassa salvavita a fine anno: l'Ultimo riceve +15M, il Penultimo +10M, il Terzultimo +5M.
    """)

# TAB 8: ADMIN (Esclusivo Admin)
if st.session_state.is_admin:
    with tab8:
        st.header("⚙️ Pannello di Controllo Amministratore")
        
        with st.expander("🛠️ 0. Regole & Parametri della Lega (Gestione Stagioni)"):
            target_season = st.text_input("Stagione di Riferimento", value=active_season)
            
            r_tranche = st.number_input("Valore Tranche Trimestrale (M)", value=int(rules['tranche_value']), step=1)
            r_cap = st.number_input("Tetto Monte Ingaggi / Salary Cap (M)", value=int(rules['salary_cap']), step=1)
            r_max_contr = st.number_input("Limite Massimo Anni Contratto per Squadra", value=int(rules['max_contract_years']), step=1)
            
            st.markdown("---")
            st.write("**Bonus Stadio per Livello:**")
            r_b_base = st.number_input("Bonus Stadio - Base", value=int(rules['bonus_base']), step=1)
            r_b_med = st.number_input("Bonus Stadio - Medio", value=int(rules['bonus_medio']), step=1)
            r_b_top = st.number_input("Bonus Stadio - Top", value=int(rules['bonus_top']), step=1)
            r_b_adv = st.number_input("Bonus Stadio - Advanced", value=int(rules['bonus_advanced']), step=1)

            st.markdown("---")
            st.write("**Costi di Manutenzione Stadio per Livello:**")
            r_m_base = st.number_input("Manutenzione Stadio - Base", value=int(rules.get('maint_base', 2)), step=1)
            r_m_med = st.number_input("Manutenzione Stadio - Medio", value=int(rules.get('maint_medio', 5)), step=1)
            r_m_top = st.number_input("Manutenzione Stadio - Top", value=int(rules.get('maint_top', 10)), step=1)
            r_m_adv = st.number_input("Manutenzione Stadio - Advanced", value=int(rules.get('maint_advanced', 15)), step=1)
            
            st.markdown("---")
            st.write("**Paracaduti Economici (Ultimi tre in classifica):**")
            r_p1 = st.number_input("Paracadute Ultimo (Rank Peggiore)", value=int(rules['paracadute_1']), step=1)
            r_p2 = st.number_input("Paracadute Penultimo", value=int(rules['paracadute_2']), step=1)
            r_p3 = st.number_input("Paracadute Terzultimo", value=int(rules['paracadute_3']), step=1)
            
            if st.button("Salva Regole per questa Stagione 💾", key="btn_salva_regole"):
                existing_season = supabase.table("league_rules").select("*").eq("season", target_season).execute()
                
                rule_payload = {
                    "season": target_season,
                    "tranche_value": int(r_tranche),
                    "salary_cap": int(r_cap),
                    "max_contract_years": int(r_max_contr),
                    "bonus_base": int(r_b_base),
                    "bonus_medio": int(r_b_med),
                    "bonus_top": int(r_b_top),
                    "bonus_advanced": int(r_b_adv),
                    "maint_base": int(r_m_base),
                    "maint_medio": int(r_m_med),
                    "maint_top": int(r_m_top),
                    "maint_advanced": int(r_m_adv),
                    "paracadute_1": int(r_p1),
                    "paracadute_2": int(r_p2),
                    "paracadute_3": int(r_p3)
                }
                
                if existing_season.data:
                    supabase.table("league_rules").update(rule_payload).eq("season", target_season).execute()
                else:
                    supabase.table("league_rules").insert(rule_payload).execute()
                    
                st.success(f"✅ Regole salvate per la stagione {target_season} in modo non retroattivo!")
                st.rerun()

        with st.expander("🛡️ 1. Gestione Squadre (Credenziali / Elimina Squadra)"):
            if teams:
                target_team_id = st.selectbox(
                    "Seleziona Squadra da Gestire", 
                    options=[t['id'] for t in teams], 
                    format_func=lambda x: next(t['name'] for t in teams if t['id'] == x), 
                    key="sel_team_cred"
                )
                target_team = next(t for t in teams if t['id'] == target_team_id)

                new_u = st.text_input("Username", value=target_team.get('username') or "", key=f"usr_{target_team_id}")
                new_p = st.text_input("Password", value=target_team.get('password') or "", key=f"pwd_{target_team_id}")
                
                col_btn1, col_btn2 = st.columns(2)
                
                if col_btn1.button("Aggiorna Credenziali 🔑", key=f"btn_upd_cred_{target_team_id}"):
                    supabase.table("teams").update({
                        "username": new_u,
                        "password": new_p
                    }).eq("id", target_team_id).execute()
                    st.success(f"Credenziali per {target_team['name']} aggiornate!")
                    st.rerun()
                    
                if col_btn2.button("Elimina Squadra 🗑️", type="primary", key=f"btn_del_team_{target_team_id}"):
                    supabase.table("players").update({
                        "team_id": None,
                        "salary": None,
                        "contract_years": None
                    }).eq("team_id", target_team_id).execute()
                    
                    supabase.table("teams").delete().eq("id", target_team_id).execute()
                    st.success(f"Squadra {target_team['name']} eliminata e giocatori rimessi nel listone!")
                    st.rerun()

        with st.expander("🏟️ 2. Configurazione Stadi"):
            if teams:
                team_stadium_id = st.selectbox("Seleziona Squadra", options=[t['id'] for t in teams], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x), key="sel_stadium_team")
                current_t = next(t for t in teams if t['id'] == team_stadium_id)
                
                nuovo_nome_stadio = st.text_input("Nome Stadio", value=current_t.get('stadium_name', 'Stadio Comunale'), key=f"nome_stadio_{team_stadium_id}")
                
                livelli_stadi = ['Base', 'Medio', 'Top', 'Advanced']
                lvl_attuale = current_t.get('stadium_level', 'Base')
                idx_lvl = livelli_stadi.index(lvl_attuale) if lvl_attuale in livelli_stadi else 0
                
                nuovo_livello = st.selectbox("Livello Stadio", options=livelli_stadi, index=idx_lvl, key=f"lvl_stadio_{team_stadium_id}")
                
                if st.button("Salva Parametri Stadio 🏟️", key=f"btn_save_stad_{team_stadium_id}"):
                    supabase.table("teams").update({
                        "stadium_name": nuovo_nome_stadio,
                        "stadium_level": nuovo_livello
                    }).eq("id", team_stadium_id).execute()
                    st.success("Stadio aggiornato!")
                    st.rerun()

        with st.expander("💰 3. Modifica Manuale Crediti & Anni"):
            if teams:
                team_to_edit_id = st.selectbox("Seleziona Squadra", options=[t['id'] for t in teams], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x), key="sel_edit_team")
                selected_team = next(t for t in teams if t['id'] == team_to_edit_id)
                
                nuovo_saldo = st.number_input("Nuovo Saldo Cassa (M)", value=int(round(float(selected_team['balance']))), step=1, key=f"num_saldo_{team_to_edit_id}")
                nuovi_anni_contratto = st.number_input("Nuovi Anni Contratto Totali", value=int(selected_team['total_contract_years']), min_value=0, max_value=int(rules['max_contract_years']), step=1, key=f"num_anni_{team_to_edit_id}")
                
                if st.button("Aggiorna Bilancio Squadra 💾", key=f"btn_upd_bal_{team_to_edit_id}"):
                    supabase.table("teams").update({
                        "balance": int(nuovo_saldo),
                        "total_contract_years": int(nuovi_anni_contratto)
                    }).eq("id", team_to_edit_id).execute()
                    registra_snapshot_finanziario(team_to_edit_id, "Modifica Manuale Admin", nuovo_saldo)
                    st.success(f"Dati di {selected_team['name']} aggiornati con successo!")
                    st.rerun()

        with st.expander("💸 4. Gestione Tranches Trimestrali & Prelievo Stipendi Massivo"):
            st.write("Gestisci l'accredito delle tranches e il prelievo degli stipendi in base all'andamento stagionale (interi, i giocatori all'estero sono esclusi dai prelievi di stipendio):")
            
            col_b1, col_b2 = st.columns(2)
            
            with col_b1:
                st.markdown("**1️⃣ Trimestre (Inizio Stagione)**")
                if st.button("Eroga 1° Trimestre (+120 Cr.) 💵"):
                    for t in teams:
                        tranche_val = 120
                        cassa_attuale = int(round(float(t['balance'])))
                        nuova_cassa = cassa_attuale + tranche_val
                        supabase.table("teams").update({"balance": int(nuova_cassa)}).eq("id", t['id']).execute()
                        registra_snapshot_finanziario(t['id'], "1° Trimestre (+120M)", nuova_cassa)
                    st.success("✅ 1° Trimestre erogato (+120M) a tutte le squadre!")
                    st.rerun()
                    
                st.markdown("**3️⃣ Trimestre**")
                if st.button("Eroga 3° Trimestre (+120 Cr.) 💵"):
                    for t in teams:
                        tranche_val = 120
                        cassa_attuale = int(round(float(t['balance'])))
                        nuova_cassa = cassa_attuale + tranche_val
                        supabase.table("teams").update({"balance": int(nuova_cassa)}).eq("id", t['id']).execute()
                        registra_snapshot_finanziario(t['id'], "3° Trimestre (+120M)", nuova_cassa)
                    st.success("✅ 3° Trimestre erogato (+120M) a tutte le squadre!")
                    st.rerun()

            with col_b2:
                st.markdown("**2️⃣ Trimestre & 1° Semestre (Scala Metà Stipendi)**")
                if st.button("Eroga 2° Trimestre (+120M) & Scala 50% Stipendi 📉"):
                    for t in teams:
                        tranche_val = 120
                        cassa_attuale = int(round(float(t['balance'])))
                        t_players = [p for p in players if p.get('team_id') == t['id'] and not check_is_abroad(p)]
                        tot_stipendi = int(sum([int(round(float(p.get('salary') or 0))) for p in t_players]))
                        meta_stipendi = int(round(tot_stipendi * 0.5))
                        
                        nuova_cassa = cassa_attuale + tranche_val - meta_stipendi
                        supabase.table("teams").update({"balance": int(nuova_cassa)}).eq("id", t['id']).execute()
                        registra_snapshot_finanziario(t['id'], "2° Trim. (+120M) & 50% Stipendi", nuova_cassa)
                    st.success("✅ 2° Trimestre erogato (+120M) e 50% degli stipendi scalati!")
                    st.rerun()

        with st.expander("📊 5. Importa / Aggiorna Listone Excel (.xlsx)"):
            uploaded_file = st.file_uploader("Scegli file Excel", type=["xlsx", "xls"], key="upd_listone")
            if uploaded_file is not None:
                try:
                    df = pd.read_excel(uploaded_file)
                    st.write("Anteprima colonne:")
                    st.dataframe(df.head(2))
                    colonne_disponibili = list(df.columns)
                    
                    with st.form("mapping_form"):
                        col_nome = st.selectbox("Colonna NOME GIOCATORE", options=colonne_disponibili)
                        col_ruolo = st.selectbox("Colonna RUOLO / MANTRA", options=colonne_disponibili)
                        col_squadra = st.selectbox("Colonna SQUADRA SERIE A", options=colonne_disponibili)
                        col_valore = st.selectbox("Colonna QUOTAZIONE / VALORE", options=colonne_disponibili)
                        
                        if st.form_submit_button("Aggiorna Listone Intelligentemente 🚀"):
                            total_rows = len(df)
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            count_aggiornati = 0
                            count_nuovi = 0
                            
                            for index, row in df.iterrows():
                                progress_bar.progress((index + 1) / total_rows)
                                status_text.text(f"Elaborazione riga {index + 1} di {total_rows}...")
                                
                                name = str(row[col_nome]).strip()
                                if not name or name.lower() == 'nan':
                                    continue
                                roles = str(row[col_ruolo]).strip().upper()
                                s_a = str(row[col_squadra]).strip()
                                if s_a.lower() == 'nan':
                                    s_a = ""
                                try:
                                    valore = int(round(float(str(row[col_valore]).replace(',', '.'))))
                                except:
                                    valore = 1
                                    
                                existing = supabase.table("players").select("*").ilike("name", name).execute()
                                if existing.data:
                                    supabase.table("players").update({
                                        "roles": roles,
                                        "serie_a_team": s_a,
                                        "current_fg_value": int(valore)
                                    }).eq("id", existing.data[0]['id']).execute()
                                    count_aggiornati += 1
                                else:
                                    supabase.table("players").insert({
                                        "name": name,
                                        "roles": roles,
                                        "serie_a_team": s_a,
                                        "current_fg_value": int(valore)
                                    }).execute()
                                    count_nuovi += 1
                                    
                            status_text.empty()
                            progress_bar.empty()
                            st.success(f"✅ Listone aggiornato! Inseriti {count_nuovi} nuovi, aggiornati {count_aggiornati}.")
                            st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")

        with st.expander("📋 6. Gestione Rose: Inizializzazione & Importazione CSV"):
            tab_singolo, tab_massivo = st.tabs(["✏️ Assegnazione Singola", "📁 Importa Rosa (CSV)"])
            
            with tab_singolo:
                st.write("Inizializza o riassegna un giocatore. (Per modificare stipendi e anni di una rosa, vai in **'📋 Rose & Svincoli'** e usa la Modifica Massiva).")
                disponibili_init = sorted([p for p in players], key=lambda x: x['name'])
                
                init_player_id = st.selectbox(
                    "Giocatore da Assegnare", 
                    options=[p['id'] for p in disponibili_init], 
                    format_func=lambda x: next((f"{p['name']} | Attuale Squadra: {next((t['name'] for t in teams if t['id'] == p.get('team_id')), 'Svincolato')} | Stipendio: {int(round(float(p.get('salary') or 0)))}M" for p in disponibili_init if p['id'] == x), "N/D"),
                    key="sel_mod_singolo"
                )
                
                p_curr = next(p for p in players if p['id'] == init_player_id)
                curr_team_id = p_curr.get('team_id')
                curr_salary = int(round(float(p_curr.get('salary') or 0)))
                curr_years = int(p_curr.get('contract_years') or 0)
                
                idx_team = [t['id'] for t in teams].index(curr_team_id) if curr_team_id in [t['id'] for t in teams] else -1
                
                new_team_id = st.selectbox(
                    "Squadra Assegnata", 
                    options=[None] + [t['id'] for t in teams], 
                    format_func=lambda x: "Svincolato (Nessuna)" if x is None else next(t['name'] for t in teams if t['id'] == x), 
                    index=(idx_team + 1),
                    key=f"team_mod_{init_player_id}"
                )
                
                new_salary = st.number_input("Stipendio / Ingaggio (M)", min_value=0, value=curr_salary, step=1, key=f"sal_mod_{init_player_id}")
                new_years = st.number_input("Anni di Contratto Residui", min_value=0, max_value=5, value=curr_years, step=1, key=f"yr_mod_{init_player_id}")
                
                if st.button("Salva Assegnazione Giocatore ✍️", key=f"btn_save_mod_{init_player_id}"):
                    upd_payload = {
                        "team_id": new_team_id,
                        "salary": new_salary,
                        "contract_years": new_years,
                        "purchase_price": new_salary,
                        "initial_contract_years": new_years,
                        "is_abroad": False
                    }
                    try:
                        supabase.table("players").update(upd_payload).eq("id", init_player_id).execute()
                    except:
                        pass
                    
                    teams_to_update = set([t for t in [curr_team_id, new_team_id] if t is not None])
                    for t_id in teams_to_update:
                        t_players_aggiornati = supabase.table("players").select("contract_years, future_contract_years").eq("team_id", t_id).execute().data
                        reale_somma_anni = sum([int(tp.get('contract_years') or 0) + int(tp.get('future_contract_years') or 0) for tp in t_players_aggiornati])
                        supabase.table("teams").update({"total_contract_years": reale_somma_anni}).eq("id", t_id).execute()
                        
                    st.success(f"✅ Dati di {p_curr['name']} aggiornati correttamente!")
                    st.rerun()

            with tab_massivo:
                st.write("Importa un file CSV estratto da Fantagazzetta/Fantacalcio (Formato atteso: Ruolo;Nome;Squadra;Quotazione Attuale).")
                csv_team_id = st.selectbox("Seleziona Squadra di Destinazione", options=[t['id'] for t in teams], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x), key="csv_team_sel")
                csv_anni = st.number_input("Anni di Contratto da assegnare a tutti i giocatori importati", min_value=1, max_value=5, value=1, step=1, key="csv_anni_input")
                addebita_cassa = st.checkbox("Addebita i costi (somma delle quotazioni) alla cassa della squadra?", value=False)
                
                csv_file = st.file_uploader("Carica File CSV", type=["csv"], key="file_csv_rosa")
                if st.button("Importa e Assegna Giocatori 🚀", key="btn_import_rosa"):
                    if csv_file is not None:
                        try:
                            df_csv = pd.read_csv(csv_file, sep=";")
                            if "Nome" not in df_csv.columns or "Quotazione Attuale" not in df_csv.columns:
                                st.error("Formato CSV non valido. Assicurati che contenga le colonne 'Nome' e 'Quotazione Attuale' separate da punto e virgola (;).")
                            else:
                                players_map = {str(p['name']).strip().lower(): p for p in players}
                                assegnati = []
                                non_trovati = []
                                tot_spesa = 0
                                
                                for idx, row in df_csv.iterrows():
                                    p_name = str(row['Nome']).strip()
                                    if p_name.lower() == 'nan' or not p_name:
                                        continue
                                    try:
                                        p_val = int(round(float(str(row['Quotazione Attuale']).replace(',', '.'))))
                                    except:
                                        p_val = 1
                                        
                                    p_match = players_map.get(p_name.lower())
                                    if p_match:
                                        upd_p = {
                                            "team_id": csv_team_id,
                                            "salary": p_val,
                                            "contract_years": csv_anni,
                                            "purchase_price": p_val,
                                            "initial_contract_years": csv_anni,
                                            "is_abroad": False
                                        }
                                        supabase.table("players").update(upd_p).eq("id", p_match['id']).execute()
                                        assegnati.append(f"{p_name} ({p_val}M)")
                                        tot_spesa += p_val
                                    else:
                                        non_trovati.append(p_name)
                                        
                                t_players_aggiornati = supabase.table("players").select("contract_years, future_contract_years").eq("team_id", csv_team_id).execute().data
                                reale_somma_anni = sum([int(tp.get('contract_years') or 0) + int(tp.get('future_contract_years') or 0) for tp in t_players_aggiornati])
                                
                                target_team = next(t for t in teams if t['id'] == csv_team_id)
                                new_bal = int(round(float(target_team['balance'])))
                                if addebita_cassa:
                                    new_bal -= tot_spesa
                                    registra_snapshot_finanziario(csv_team_id, f"Import CSV ({len(assegnati)} giocatori)", new_bal)
                                    
                                supabase.table("teams").update({
                                    "total_contract_years": reale_somma_anni,
                                    "balance": new_bal
                                }).eq("id", csv_team_id).execute()
                                
                                if assegnati:
                                    st.success(f"✅ Importati {len(assegnati)} giocatori con successo per la squadra {target_team['name']}: {', '.join(assegnati)}")
                                if non_trovati:
                                    st.warning(f"⚠️ {len(non_trovati)} giocatori non trovati nel database e ignorati: {', '.join(non_trovati)}")
                                
                        except Exception as e:
                            st.error(f"Errore durante la lettura del file: {e}")
                    else:
                        st.error("Carica prima il file CSV.")

        with st.expander("✈️ 7. Giocatori Trasferiti all'Estero (Congelamento Stipendio & Peso Contratti)"):
            st.write("Registra o aggiorna un giocatore andato all'estero nella realtà. Il giocatore **pesa sugli anni di contratto**, ma il suo **stipendio viene congelato** (non impatta sul monte ingaggi né sulla cassa):")
            team_estero_id = st.selectbox("Squadra Detentrice del Contratto", options=[t['id'] for t in teams], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x), key="team_estero_sel")
            
            opzioni_giocatori_estero = sorted([p for p in players], key=lambda x: x['name'])
            p_estero_id = st.selectbox("Seleziona Giocatore dal Database (oppure digita sotto per nuovo)", options=[p['id'] for p in opzioni_giocatori_estero], format_func=lambda x: next(f"{p['name']} ({p.get('serie_a_team', 'N/D')})" for p in opzioni_giocatori_estero if p['id'] == x), key="p_estero_sel")
            
            p_est_obj = next((p for p in opzioni_giocatori_estero if p['id'] == p_estero_id), None)
            def_sal = int(round(float(p_est_obj.get('salary') or 0))) if p_est_obj and p_est_obj.get('salary') is not None else 5
            def_yr = int(p_est_obj.get('contract_years') or 0) if p_est_obj and p_est_obj.get('contract_years') is not None else 2
            
            nuovo_nome_estero = st.text_input("Se il giocatore non è in lista, inserisci qui il Nome Completo (altrimenti lascia vuoto)", key=f"new_name_est_{p_estero_id}")
            estero_ruoli = st.text_input("Ruolo/Mantra (es. A, PC)", value="A", key=f"role_est_{p_estero_id}")
            estero_stipendio = st.number_input("Stipendio Congelato (M)", min_value=1, value=def_sal, step=1, key=f"sal_est_{p_estero_id}")
            estero_anni = st.number_input("Anni di Contratto Rimanenti", min_value=1, max_value=5, value=def_yr, step=1, key=f"yr_est_{p_estero_id}")
            
            col_e1, col_e2 = st.columns(2)
            
            if col_e1.button("Imposta / Salva Giocatore all'Estero ✈️", key=f"btn_save_est_{p_estero_id}"):
                if nuovo_nome_estero.strip():
                    target_name = nuovo_nome_estero.strip()
                    check_exist = supabase.table("players").select("*").ilike("name", target_name).execute().data
                    if check_exist:
                        target_pid = check_exist[0]['id']
                        upd_obj = {
                            "team_id": team_estero_id,
                            "salary": int(estero_stipendio),
                            "contract_years": int(estero_anni),
                            "serie_a_team": "Estero"
                        }
                        try:
                            supabase.table("players").update({**upd_obj, "is_abroad": True}).eq("id", target_pid).execute()
                        except:
                            supabase.table("players").update(upd_obj).eq("id", target_pid).execute()
                    else:
                        ins_obj = {
                            "name": target_name,
                            "roles": estero_ruoli.upper().strip(),
                            "serie_a_team": "Estero",
                            "team_id": team_estero_id,
                            "salary": int(estero_stipendio),
                            "contract_years": int(estero_anni),
                            "current_fg_value": 1
                        }
                        try:
                            supabase.table("players").insert({**ins_obj, "is_abroad": True}).execute()
                        except:
                            supabase.table("players").insert(ins_obj).execute()
                else:
                    upd_sel = {
                        "team_id": team_estero_id,
                        "salary": int(estero_stipendio),
                        "contract_years": int(estero_anni),
                        "serie_a_team": "Estero"
                    }
                    try:
                        supabase.table("players").update({**upd_sel, "is_abroad": True}).eq("id", p_estero_id).execute()
                    except:
                        supabase.table("players").update(upd_sel).eq("id", p_estero_id).execute()
                    
                for team_obj in teams:
                    t_id = team_obj['id']
                    t_players_aggiornati = supabase.table("players").select("contract_years, future_contract_years").eq("team_id", t_id).execute().data
                    reale_somma_anni = sum([int(tp.get('contract_years') or 0) + int(tp.get('future_contract_years') or 0) for tp in t_players_aggiornati])
                    supabase.table("teams").update({"total_contract_years": reale_somma_anni}).eq("id", t_id).execute()
                    
                st.success("✅ Giocatore registrato all'estero: contratto conteggiato negli anni totali, ma stipendio escluso da monte ingaggi e cassa!")
                st.rerun()
                
            if col_e2.button("Rientro in Italia (Scongela Stipendio) 🇮🇹", key=f"btn_rit_ita_{p_estero_id}"):
                try:
                    supabase.table("players").update({"is_abroad": False}).eq("id", p_estero_id).execute()
                except:
                    pass
                st.success("🇮🇹 Giocatore rientrato in Italia: stipendio regolarmente riattivato nel monte ingaggi!")
                st.rerun()

        # PROCEDURA DI FINE STAGIONE STEP-BY-STEP
        with st.expander("🏁 8. Procedura Guidata di Fine Stagione (In Ordine Rigoroso)"):
            st.write("Esegui le operazioni di chiusura stagione in ordine. Per ogni passaggio potrai decidere se applicarlo a tutte le squadre o escluderne alcune.")
            
            livelli_stadi_order = ['Base', 'Medio', 'Top', 'Advanced']
            team_names_map = {t['id']: t['name'] for t in teams}

            st.markdown("#### 1️⃣ Passo 1: Accredito Ultima Tranche Trimestrale (+120M)")
            st.write("Accredita i 120M di cassa per l'ultimo trimestre.")
            opt_tranche = st.radio("Vuoi accreditare l'ultima tranche a tutte le squadre?", ["Sì, a tutte le squadre", "No, escludi alcune squadre"], key="rad_tranche")
            escluse_tranche = []
            if opt_tranche == "No, escludi alcune squadre":
                escluse_tranche = st.multiselect("Seleziona squadre da ESCLUDERE dall'accredito tranche:", options=[t['id'] for t in teams], format_func=lambda x: team_names_map[x], key="ms_tranche")
            
            if st.button("Esegui Accredito Ultima Tranche 💵", key="btn_step1_tranche"):
                applicate = 0
                for t in teams:
                    if t['id'] not in escluse_tranche:
                        cassa_attuale = int(round(float(t['balance'])))
                        nuova_cassa = cassa_attuale + 120
                        supabase.table("teams").update({"balance": int(nuova_cassa)}).eq("id", t['id']).execute()
                        registra_snapshot_finanziario(t['id'], "Accredito Ultima Tranche (+120M)", nuova_cassa)
                        applicate += 1
                st.success(f"✅ Ultima tranche di 120M accreditata a {applicate} squadre!")
                st.rerun()

            st.divider()

            st.markdown("#### 2️⃣ Passo 2: Pagamento Saldo Stipendi (Ultima Metà)")
            st.write("Scala la restante metà degli stipendi annui (esclusi i giocatori all'estero).")
            opt_stipendi = st.radio("Vuoi scalare il saldo stipendi a tutte le squadre?", ["Sì, a tutte le squadre", "No, escludi alcune squadre"], key="rad_stipendi")
            escluse_stipendi = []
            if opt_stipendi == "No, escludi alcune squadre":
                escluse_stipendi = st.multiselect("Seleziona squadre da ESCLUDERE dal pagamento stipendi:", options=[t['id'] for t in teams], format_func=lambda x: team_names_map[x], key="ms_stipendi")
                
            if st.button("Esegui Prelievo Saldo Stipendi 📉", key="btn_step2_stipendi"):
                applicate = 0
                for t in teams:
                    if t['id'] not in escluse_stipendi:
                        cassa_attuale = int(round(float(t['balance'])))
                        t_players = [p for p in players if p.get('team_id') == t['id'] and not check_is_abroad(p)]
                        tot_stipendi = int(sum([int(round(float(p.get('salary') or 0))) for p in t_players]))
                        meta_stipendi = int(round(tot_stipendi * 0.5))
                        nuova_cassa = cassa_attuale - meta_stipendi
                        supabase.table("teams").update({"balance": int(nuova_cassa)}).eq("id", t['id']).execute()
                        registra_snapshot_finanziario(t['id'], "Saldo Stipendi (Ultima Metà)", nuova_cassa)
                        applicate += 1
                st.success(f"✅ Saldo stipendi prelevato con successo da {applicate} squadre!")
                st.rerun()

            st.divider()

            st.markdown("#### 3️⃣ Passo 3: Pagamento Manutenzione Stadio & Accredito Bonus")
            st.write("Applica il saldo netto dello stadio (Bonus - Manutenzione). Se una squadra viene esclusa dal pagamento della manutenzione, **il suo stadio retrocede di un livello**.")
            opt_stadio = st.radio("Vuoi far pagare la manutenzione e accreditare il bonus a tutte le squadre?", ["Sì, a tutte le squadre", "No, escludi alcune squadre"], key="rad_stadio")
            escluse_stadio = []
            if opt_stadio == "No, escludi alcune squadre":
                escluse_stadio = st.multiselect("Seleziona squadre che NON PAGANO la manutenzione (retrocederanno di livello):", options=[t['id'] for t in teams], format_func=lambda x: team_names_map[x], key="ms_stadio")
                
            if st.button("Esegui Saldo Manutenzione / Bonus Stadio 🏟️", key="btn_step3_stadio"):
                for t in teams:
                    t_id = t['id']
                    t_lvl = t.get('stadium_level', 'Base')
                    idx_attuale = livelli_stadi_order.index(t_lvl) if t_lvl in livelli_stadi_order else 0
                    cassa_attuale = int(round(float(t['balance'])))
                    
                    if t_id not in escluse_stadio:
                        bonus_spettante = int(valori_bonus.get(t_lvl, int(rules['bonus_base'])))
                        costo_manutenzione = int(valori_maint.get(t_lvl, int(rules.get('maint_base', 2))))
                        netto_stadio = bonus_spettante - costo_manutenzione
                        nuova_cassa = cassa_attuale + netto_stadio
                        supabase.table("teams").update({"balance": int(nuova_cassa)}).eq("id", t_id).execute()
                        registra_snapshot_finanziario(t_id, f"Saldo Stadio ({netto_stadio:+d}M)", nuova_cassa)
                    else:
                        nuovo_lvl = livelli_stadi_order[max(0, idx_attuale - 1)]
                        supabase.table("teams").update({"stadium_level": nuovo_lvl}).eq("id", t_id).execute()
                        st.warning(f"⚠️ {t['name']} non ha pagato la manutenzione: stadio declassato a {nuovo_lvl}!")
                        
                st.success("✅ Saldo stadi elaborato e livelli aggiornati con successo!")
                st.rerun()

            st.divider()

            st.markdown("#### 4️⃣ Passo 4: Svincolo Giocatori in Scadenza e Attivazione Rinnovi")
            st.write("Svincola automaticamente i giocatori a fine contratto (1 anno rimasto). Se un giocatore è stato **Rinnovato** tramite il pulsante apposito nella rosa, NON verrà svincolato e il suo nuovo stipendio e anni diventeranno attivi.")
            opt_svincolo = st.radio("Vuoi eseguire lo svincolo automatico per tutte le squadre?", ["Sì, a tutte le squadre", "No, escludi alcune squadre"], key="rad_svincolo")
            escluse_svincolo = []
            if opt_svincolo == "No, escludi alcune squadre":
                escluse_svincolo = st.multiselect("Seleziona squadre da ESCLUDERE dallo svincolo automatico:", options=[t['id'] for t in teams], format_func=lambda x: team_names_map[x], key="ms_svincolo")
                
            if st.button("Esegui Svincoli e Attiva Rinnovi ❌", key="btn_step4_svincolo"):
                count_svincolati = 0
                count_rinnovati = 0
                for t in teams:
                    if t['id'] not in escluse_svincolo:
                        scadenti_team = [p for p in players if p.get('team_id') == t['id'] and int(p.get('contract_years') or 0) <= 1]
                        for sc_p in scadenti_team:
                            fut_sal = sc_p.get('future_salary')
                            fut_yr = sc_p.get('future_contract_years')
                            
                            if fut_sal and fut_yr:
                                upd_rinnovo = {
                                    "salary": int(fut_sal),
                                    "contract_years": int(fut_yr),
                                    "future_salary": None,
                                    "future_contract_years": None
                                }
                                try:
                                    supabase.table("players").update(upd_rinnovo).eq("id", sc_p['id']).execute()
                                except:
                                    pass
                                count_rinnovati += 1
                            else:
                                upd_sv = {"team_id": None, "salary": None, "contract_years": None, "is_under_21": False, "future_salary": None, "future_contract_years": None}
                                try:
                                    supabase.table("players").update({**upd_sv, "is_abroad": False}).eq("id", sc_p['id']).execute()
                                except:
                                    supabase.table("players").update(upd_sv).eq("id", sc_p['id']).execute()
                                count_svincolati += 1
                            
                        t_aggiornati = supabase.table("players").select("contract_years, future_contract_years").eq("team_id", t['id']).execute().data
                        reale_somma = sum([int(tp.get('contract_years') or 0) + int(tp.get('future_contract_years') or 0) for tp in t_aggiornati])
                        supabase.table("teams").update({"total_contract_years": reale_somma}).eq("id", t['id']).execute()
                        
                st.success(f"✅ Eseguiti {count_svincolati} svincoli per fine contratto e attivati {count_rinnovati} nuovi rinnovi!")
                st.rerun()

            st.divider()

            st.markdown("#### 5️⃣ Passo 5: Archiviazione Ufficiale nell'Albo d'Oro & Reset Classifica")
            st.write("Salva la classifica finale ufficiale e tutte le partite della stagione nell'Albo d'Oro. **Una volta archiviato, i risultati vengono ripuliti e la classifica in Schermata 1 si azzera automaticamente** per iniziare la nuova stagione.")
            stagione_da_archiviare = st.text_input("Nome Stagione da Archiviare:", value=active_season, key="txt_hof_save")
            
            if st.button("Salva Stagione nell'Albo d'Oro & Azzera Classifica 🏛️", key="btn_step5_hof"):
                try:
                    tutti_i_match = supabase.table("match_results").select("*").eq("season", active_season).execute().data
                except:
                    tutti_i_match = []
                    
                payload_hof = {
                    "season": stagione_da_archiviare,
                    "final_standings": classifica_ordinata,
                    "match_results": tutti_i_match
                }
                
                try:
                    check_esistente = supabase.table("hall_of_fame_seasons").select("id").eq("season", stagione_da_archiviare).execute().data
                    if check_esistente:
                        supabase.table("hall_of_fame_seasons").update(payload_hof).eq("season", stagione_da_archiviare).execute()
                    else:
                        supabase.table("hall_of_fame_seasons").insert(payload_hof).execute()
                    
                    supabase.table("match_results").delete().eq("season", active_season).execute()
                    
                    st.success(f"🎉 Stagione {stagione_da_archiviare} archiviata con successo nell'Albo d'Oro! La classifica in Schermata 1 è stata azzerata per la nuova stagione.")
                    st.rerun()
                except Exception as err:
                    st.error(f"⚠️ Errore durante l'archiviazione: {err}")
                    st.info("💡 Assicurati che la tabella esista eseguendo questo comando nell'SQL Editor di Supabase:")
                    st.code("CREATE TABLE IF NOT EXISTS public.hall_of_fame_seasons (id BIGSERIAL PRIMARY KEY, season TEXT UNIQUE NOT NULL, final_standings JSONB, match_results JSONB, created_at TIMESTAMPTZ DEFAULT NOW());\nALTER TABLE public.hall_of_fame_seasons DISABLE ROW LEVEL SECURITY;", language="sql")