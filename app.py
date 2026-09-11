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
        "tranche_value": 100,
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

def calcola_10_percento(valore):
    bonus = valore * 0.1
    parte_decimale = bonus - int(bonus)
    risultato = int(bonus) if parte_decimale <= 0.5 else int(bonus) + 1
    return max(1, risultato)

def registra_snapshot_finanziario(team_id, etichetta, saldo_attuale):
    try:
        supabase.table("financial_history").insert({
            "team_id": team_id,
            "season": active_season,
            "event_label": etichetta,
            "balance_snapshot": saldo_attuale
        }).execute()
    except:
        pass

def render_role_badge(role_str):
    if not role_str:
        return ""
    color_map = {
        'P': '#f39c12',
        'DS': '#27ae60', 'DC': '#27ae60', 'DD': '#27ae60', 'B': '#27ae60',
        'E': '#2980b9', 'M': '#2980b9', 'C': '#2980b9',
        'W': '#8e44ad', 'T': '#8e44ad',
        'A': '#c0392b', 'PC': '#c0392b'
    }
    roles = [r.strip().upper() for r in str(role_str).replace('/', ',').split(',')]
    html = ""
    for r in roles:
        bg = color_map.get(r, '#7f8c8d')
        html += f'<span style="background-color: {bg}; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; margin-right: 4px; display: inline-block; text-align: center;">{r}</span>'
    return html

# --- GESTIONE AUTENTICAZIONE E REGISTRAZIONE ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.is_admin = False
    st.session_state.team_id = None

if not st.session_state.authenticated:
    st.title("🔐 Accesso & Registrazione - FantaGestionale")
    
    tab_login, tab_register = st.tabs(["🔑 Accedi", "📝 Registra Nuova Squadra"])
    
    with tab_login:
        with st.form("login_form"):
            u_input = st.text_input("Username Squadra")
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
                    if a_input == ADMIN_SECRET_PWD:
                        st.session_state.is_admin = True
                        st.success("Accesso effettuato come Amministratore!")
                    else:
                        st.session_state.is_admin = False
                        st.success(f"Accesso effettuato per la squadra: {matched_team['name']}")
                    st.rerun()
                else:
                    st.error("Credenziali non valide o username/password errati.")
                    
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
    st.write(f"Utente: **{st.session_state.username}**")
    st.write(f"📅 Stagione: **{active_season}**")
    if st.session_state.is_admin:
        st.info("🛠️ Ruolo: Amministratore")
    else:
        st.info("👤 Ruolo: Utente Standard")
    
    if st.button("Disconnetti 🚪"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.session_state.is_admin = False
        st.session_state.team_id = None
        st.rerun()

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

# Definizione delle Tab in base al ruolo con indici coerenti
if st.session_state.is_admin:
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Dashboard & Finanze", "📈 Monte Ingaggi & Tax", "📋 Rose & Svincoli", 
        "👶 Panchina U21", "🤝 Scambi & Prestiti", "⚽ Inserimento Giornate", 
        "⚽ Mercato", "⚙️ Admin"
    ])
else:
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Dashboard & Finanze", "📈 Monte Ingaggi & Tax", "📋 La Mia Rosa & Previsioni", 
        "👶 Panchina U21", "🤝 Scambi & Prestiti", "⚽ Inserimento Giornate"
    ])

# TAB 1: DASHBOARD, CLASSIFICA, MONTEPREMI & GRAFICO FINANZIARIO
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
    totale_pool_euro = num_squadre * 20.0
    premio_1 = totale_pool_euro * 0.70
    premio_2 = totale_pool_euro * 0.30
    premio_3 = 20.0
    
    if len(classifica_ordinata) >= 1:
        classifica_ordinata[0]['montepremi'] = f"🥇 {premio_1:.2f} € (70%)"
    if len(classifica_ordinata) >= 2:
        classifica_ordinata[1]['montepremi'] = f"🥈 {premio_2:.2f} € (30%)"
    if len(classifica_ordinata) >= 3:
        classifica_ordinata[2]['montepremi'] = f"🥉 {premio_3:.2f} € (Rimborso)"
    for item in classifica_ordinata[3:]:
        item['montepremi'] = "0.00 €"

    if classifica_ordinata:
        st.write(f"💵 **Pool Montepremi Totale (Quota 20€ x {num_squadre} squadre):** {totale_pool_euro:.2f} €")
        df_rank = pd.DataFrame(classifica_ordinata)
        df_rank.index = range(1, len(df_rank) + 1)
        df_rank.columns = ["Squadra", "Punti", "Punti Totali Giornate", "Partite Giocate", "Premio Stimato"]
        st.dataframe(df_rank, use_container_width=True)
        st.divider()

    st.header("📈 Andamento Finanziario Squadre (Grafico Azionario)")
    st.write("Visualizzazione grafica in tempo reale dell'andamento economico della cassa delle squadre ad ogni aggiornamento.")
    
    if fin_history_res:
        df_fin = pd.DataFrame(fin_history_res)
        id_to_name = {t['id']: t['name'] for t in teams}
        df_fin['Squadra'] = df_fin['team_id'].map(id_to_name)
        
        if 'timestamp' in df_fin.columns and 'balance_snapshot' in df_fin.columns:
            pivot_fin = df_fin.pivot_table(index='timestamp', columns='Squadra', values='balance_snapshot')
            st.line_chart(pivot_fin)
        else:
            st.info("Dati finanziari insufficienti per il tracciamento grafico.")
    else:
        st.info("Nessuno storico economico registrato al momento. Verrà popolato man mano che si effettuano operazioni di cassa.")

    st.header("Situazione Finanziaria & Stadi")
    if not teams:
        st.info("Nessuna squadra presente.")
    else:
        for team in teams:
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.write(f"🛡️ **{team['name']}**")
            col2.write(f"💰 Cassa: **{team['balance']} M**")
            col3.write(f"👶 Budget U21: **{team.get('u21_balance', 30)} M**")
            s_name = team.get('stadium_name', 'Stadio Comunale')
            s_level = team.get('stadium_level', 'Base')
            col4.write(f"🏟️ **{s_name}** ({s_level})")
            col5.write(f"📜 Anni Contratto: **{team['total_contract_years']}/{rules['max_contract_years']}**")
            st.divider()

# TAB 2: MONTE INGAGGI & LUXURY TAX
with tab2:
    st.header(f"📈 Monitor Monte Ingaggi & Luxury Tax (Tetto: {rules['salary_cap']}M)")
    if not teams:
        st.info("Nessuna squadra presente.")
    else:
        SALARY_CAP = float(rules['salary_cap'])
        dati_tax = []
        totale_tax_raccolta = 0
        
        rank_map = {item['name']: idx+1 for idx, item in enumerate(classifica_ordinata)}
        
        for team in teams:
            t_players = [p for p in players if p.get('team_id') == team['id']]
            monte_ingaggi = sum([p.get('salary', 0) for p in t_players])
            sforo = max(0, monte_ingaggi - SALARY_CAP)
            tassa_dovuta = sforo * 0.5 
            totale_tax_raccolta += tassa_dovuta
            
            calc_rank = rank_map.get(team['name'], 1)
            
            dati_tax.append({
                "team_id": team['id'],
                "name": team['name'],
                "monte_ingaggi": monte_ingaggi,
                "sforo": sforo,
                "tassa": tassa_dovuta,
                "ranking": calc_rank
            })
            
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.write(f"🛡️ **{team['name']}** (Rank Classifica: {calc_rank})")
            col_b.write(f"💵 Monte Ingaggi: **{monte_ingaggi}M** / {SALARY_CAP}M")
            if sforo > 0:
                col_c.markdown(f"<span style='color: #c0392b; font-weight: bold;'>Sforo: +{sforo}M 🔴</span>", unsafe_allow_html=True)
                col_d.markdown(f"<span style='color: #c0392b; font-weight: bold;'>Luxury Tax: {tassa_dovuta}M</span>", unsafe_allow_html=True)
            else:
                col_c.markdown("<span style='color: #27ae60;'>In regola 🟢</span>", unsafe_allow_html=True)
                col_d.write("Luxury Tax: 0M")
            st.divider()
            
        st.subheader("💡 Simulazione Previsionale Distribuzione a 'Cascade' della Luxury Tax")
        st.write(f"Totale Luxury Tax accumulata dalle squadre oltre il cap: **{totale_tax_raccolta} M**")
        
        virtuose = [d for d in dati_tax if d['sforo'] == 0]
        if virtuose and totale_tax_raccolta > 0:
            virtuose_ordinate = sorted(virtuose, key=lambda x: x['ranking'])
            quota_base = totale_tax_raccolta / len(virtuose_ordinate)
            
            st.write("Previsione di distribuzione della tassa tra le squadre virtuose in base al piazzamento in classifica:")
            for v in virtuose_ordinate:
                st.markdown(f"- **{v['name']}** (Rank {v['ranking']}): riceverebbe stimati **+{quota_base:.1f} M**")
        else:
            st.info("Nessuna squadra virtuosa o tassa accumulata al momento.")

# TAB 3: ROSE, SVINCOLI & CESSIONI ALL'ESTERO
with tab3:
    if st.session_state.is_admin:
        st.header("Gestione Rose (Admin)")
        selected_team_id = st.selectbox("Seleziona Squadra", options=[t['id'] for t in teams], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x), key="select_squadra_rose")
    else:
        selected_team_id = st.session_state.team_id
        st.header("La Mia Rosa & Dashboard Preventiva (Lungo Termine)")

    if teams:
        team_players = [p for p in players if p.get('team_id') == selected_team_id]
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
            h6.markdown("**Azioni**")
            st.divider()

            for p in team_players:
                col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 1, 1, 1])
                badge_html = render_role_badge(p.get('roles', ''))
                squadra_sa = f" ({p.get('serie_a_team', '')})" if p.get('serie_a_team') else ""
                
                col1.markdown(f"{badge_html} **{p['name']}**{squadra_sa}", unsafe_allow_html=True)
                
                stipendio_contratto = p.get('salary', 0)
                quotazione_attuale = p.get('current_fg_value', 0)
                
                col2.write(f"{stipendio_contratto} M")
                col3.write(f"{quotazione_attuale} M")
                
                differenza = quotazione_attuale - stipendio_contratto
                if differenza > 0:
                    col4.markdown(f"<span style='color: #27ae60; font-weight: bold;'>+{differenza} M 🟢</span>", unsafe_allow_html=True)
                elif differenza < 0:
                    col4.markdown(f"<span style='color: #c0392b; font-weight: bold;'>{differenza} M 🔴</span>", unsafe_allow_html=True)
                else:
                    col4.markdown("<span style='color: #7f8c8d;'>0 M</span>", unsafe_allow_html=True)
                
                col5.write(f"{p.get('contract_years', 0)} anni")
                
                btn_svincola = col6.button("Svincola ❌", key=f"svincola_{p['id']}")
                btn_estero = col6.button("Cedi Estero ✈️", key=f"estero_{p['id']}")
                
                if btn_svincola:
                    penale = calcola_10_percento(stipendio_contratto)
                    nuova_cassa = team_data['balance'] - penale
                    nuovi_anni = team_data['total_contract_years'] - p['contract_years']
                    
                    if nuova_cassa < 0:
                        st.error(f"Fondi insufficienti per pagare la penale ({penale}M).")
                    else:
                        try:
                            supabase.table("transfer_history").insert({"player_name": p['name'], "team_id": selected_team_id}).execute()
                        except:
                            pass
                            
                        supabase.table("players").update({"team_id": None, "salary": None, "contract_years": None, "is_under_21": False}).eq("id", p['id']).execute()
                        supabase.table("teams").update({"balance": nuova_cassa, "total_contract_years": nuovi_anni}).eq("id", selected_team_id).execute()
                        registra_snapshot_finanziario(selected_team_id, f"Svincolo {p['name']}", nuova_cassa)
                        st.success(f"{p['name']} svincolato!")
                        st.rerun()
                        
                if btn_estero:
                    p_price = float(p.get('purchase_price') or stipendio_contratto)
                    tot_anni = int(p.get('initial_contract_years') or 3)
                    anni_res = int(p.get('contract_years') or 1)
                    valore_residuo = (p_price / max(1, tot_anni)) * anni_res
                    
                    nuova_cassa = team_data['balance'] + valore_residuo
                    nuovi_anni = team_data['total_contract_years'] - p['contract_years']
                    
                    try:
                        supabase.table("transfer_history").insert({"player_name": p['name'], "team_id": selected_team_id}).execute()
                    except:
                        pass
                        
                    supabase.table("players").update({"team_id": None, "salary": None, "contract_years": None, "is_under_21": False}).eq("id", p['id']).execute()
                    supabase.table("teams").update({"balance": nuova_cassa, "total_contract_years": nuovi_anni}).eq("id", selected_team_id).execute()
                    registra_snapshot_finanziario(selected_team_id, f"Cessione Estero {p['name']}", nuova_cassa)
                    st.success(f"✈️ {p['name']} ceduto all'estero! Incassati {valore_residuo:.1f}M (valore residuo ammortato).")
                    st.rerun()

            st.markdown("---")
            st.subheader("🔮 Dashboard Preventiva & Analisi Contrattuale (Prossima Stagione)")
            st.write("Panoramica della rosa in ottica futura, con classi di costo e contratti a lungo termine.")
            
            costo_totale_attuale = sum([p.get('salary', 0) for p in team_players])
            giocatori_in_scadenza = [p for p in team_players if p.get('contract_years', 0) <= 1]
            anni_residui_totali = sum([p.get('contract_years', 0) for p in team_players])
            
            p_col1, p_col2, p_col3 = st.columns(3)
            p_col1.metric("Monte Ingaggi Attuale", f"{costo_totale_attuale} M")
            p_col2.metric("Giocatori in Scadenza (1 anno)", len(giocatori_in_scadenza))
            p_col3.metric("Anni Contratto Occupati", f"{anni_residui_totali} / {rules['max_contract_years']}")
            
            if giocatori_in_scadenza:
                st.write("⚠️ **Attenzione ai rinnovi / scadenze imminenti:**")
                scadenze_nomi = ", ".join([f"{p['name']} ({p.get('salary', 0)}M)" for p in giocatori_in_scadenza])
                st.info(scadenze_nomi)
            else:
                st.success("✅ Nessun giocatore in scadenza immediata per la prossima stagione.")

# TAB 4: PANCHINA UNDER 21
with tab4:
    if st.session_state.is_admin:
        st.header("👶 Gestione Panchina Under 21 (Admin)")
        selected_u21_team_id = st.selectbox("Seleziona Squadra", options=[t['id'] for t in teams], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x), key="select_u21_team_admin")
    else:
        selected_u21_team_id = st.session_state.team_id
        st.header("👶 La Tua Panchina Under 21 (Budget Separato 30M)")

    if teams:
        team_u21_data = next(t for t in teams if t['id'] == selected_u21_team_id)
        current_u21_balance = float(team_u21_data.get('u21_balance', 30))
        
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
                col_u3.write(f"{g.get('budget_used', 0)} M")
                
                presenze = g.get('presenze', 0)
                stato_presenze = f"🔥 {presenze} / 5" if presenze < 5 else f"✅ {presenze} / 5 (Obbligo Contratto Raggiunto!)"
                col_u4.write(stato_presenze)
                
                if st.session_state.is_admin:
                    if col_u5.button("Svincola U21 ❌", key=f"svincola_u21_{g['id']}"):
                        refund = float(g.get('budget_used', 0))
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
                                "budget_used": costo_u21,
                                "presenze": 0
                            }).execute()
                            
                            supabase.table("teams").update({
                                "u21_balance": current_u21_balance - costo_u21
                            }).eq("id", selected_u21_team_id).execute()
                            
                            supabase.table("players").update({"team_id": selected_u21_team_id, "salary": 0, "contract_years": 0, "is_under_21": True}).eq("id", selected_u21_player).execute()
                            
                            st.success(f"✅ {p_obj['name']} inserito con successo nella Panchina U21!")
                            st.rerun()

# TAB 5: SCAMBI & PRESTITI
with tab5:
    st.header("🤝 Mercato Avanzato: Scambi & Prestiti")
    
    if not teams:
        st.warning("Nessuna squadra presente.")
    else:
        user_team_id = st.session_state.team_id if not st.session_state.is_admin else teams[0]['id']
        
        tab_scambio, tab_prestito, tab_storico_scambi = st.tabs(["🔄 Proponi Scambio Diretto", "📋 Gestione Prestiti", "📨 Richieste Scambio Ricevute"])
        
        with tab_scambio:
            st.write("Crea una proposta di scambio con un'altra squadra. *Nota: Il differenziale delle quotazioni Mantra tra i giocatori scambiati non deve superare il 10%, altrimenti va colmato con un conguaglio in crediti.*")
            
            with st.form("proponi_scambio_form"):
                ricevente_id = st.selectbox("Squadra Destinataria", options=[t['id'] for t in teams if t['id'] != user_team_id], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x))
                
                miei_giocatori = [p for p in players if p.get('team_id') == user_team_id]
                miei_offerti = st.multiselect("Seleziona tuoi giocatori da OFFRIRE", options=miei_giocatori, format_func=lambda x: f"{x['name']} (Q: {x.get('current_fg_value', 1)}M)")
                
                giocatori_altra = [p for p in players if p.get('team_id') == ricevente_id]
                loro_richiesti = st.multiselect("Seleziona giocatori da RICHIEDERE", options=giocatori_altra, format_func=lambda x: f"{x['name']} (Q: {x.get('current_fg_value', 1)}M)")
                
                conguaglio = st.number_input("Conguaglio in Crediti (positivo se paghi tu, negativo se ricevi)", value=0.0, step=1.0)
                
                if st.form_submit_button("Invia Proposta di Scambio 🤝"):
                    if not miei_offerti or not loro_richiesti:
                        st.error("Seleziona almeno un giocatore da offrire e uno da richiedere.")
                    else:
                        valore_offerto = sum([p.get('current_fg_value', 1) for p in miei_offerti]) + conguaglio
                        valore_richiesto = sum([p.get('current_fg_value', 1) for p in loro_richiesti])
                        
                        differenza = abs(valore_offerto - valore_richiesto)
                        tolleranza = max(valore_offerto, valore_richiesto) * 0.10
                        
                        if differenza > tolleranza:
                            st.error(f"❌ Scambio non valido: il differenziale di valore supera il 10% consentito (Delta: {differenza:.1f}M, Max tollerato: {tolleranza:.1f}M). Aggiusta il conguaglio!")
                        else:
                            offerti_str = ",".join([str(p['id']) for p in miei_offerti])
                            richiesti_str = ",".join([str(p['id']) for p in loro_richiesti])
                            
                            supabase.table("trades").insert({
                                "sender_team_id": user_team_id,
                                "receiver_team_id": ricevente_id,
                                "offered_player_ids": offerti_str,
                                "requested_player_ids": richiesti_str,
                                "cash_adjustment": conguaglio,
                                "status": "In Attesa",
                                "season": active_season
                            }).execute()
                            st.success("✅ Proposta di scambio inviata con successo!")
                            st.rerun()

        with tab_prestito:
            st.write("Gestisci i prestiti dei giocatori (con divisione dello stipendio e blocco dello svincolo unilaterale).")
            
            with st.form("registra_prestito_form"):
                proprietario_id = st.selectbox("Squadra Proprietaria del Cartellino", options=[t['id'] for t in teams], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x))
                giocatori_prop = [p for p in players if p.get('team_id') == proprietario_id]
                
                if giocatori_prop:
                    giocatore_prestito_id = st.selectbox("Giocatore in Prestito", options=[p['id'] for p in giocatori_prop], format_func=lambda x: next(f"{p['name']} (Stipendio: {p.get('salary', 0)}M)" for p in giocatori_prop if p['id'] == x))
                    destinatario_prestito_id = st.selectbox("Squadra Prestataria (Chi riceve)", options=[t['id'] for t in teams if t['id'] != proprietario_id], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x))
                    perc_stipendio = st.slider("Percentuale di stipendio pagata dalla squadra in prestito (%)", min_value=0, max_value=100, value=100, step=10)
                    
                    if st.form_submit_button("Formalizza Prestito 📋"):
                        supabase.table("loans").insert({
                            "player_id": giocatore_prestito_id,
                            "owner_team_id": proprietario_id,
                            "borrower_team_id": destinatario_prestito_id,
                            "salary_percentage_borrower": perc_stipendio,
                            "season": active_season
                        }).execute()
                        supabase.table("players").update({"team_id": destinatario_prestito_id}).eq("id", giocatore_prestito_id).execute()
                        st.success("✅ Contratto di prestito registrato! Il giocatore è stato trasferito temporaneamente e protetto da svincolo unilaterale.")
                        st.rerun()
                else:
                    st.info("La squadra selezionata non ha giocatori in rosa.")
                    
            st.write("**Prestiti Attivi:**")
            if loans_res:
                for l in loans_res:
                    p_obj = next((p for p in players if p['id'] == l['player_id']), None)
                    owner_obj = next((t for t in teams if t['id'] == l['owner_team_id']), None)
                    borrower_obj = next((t for t in teams if t['id'] == l['borrower_team_id']), None)
                    if p_obj and owner_obj and borrower_obj:
                        st.markdown(f"- 📋 **{p_obj['name']}** (Proprietario: {owner_obj['name']} ➔ In prestito a: {borrower_obj['name']} | Stipendio a carico del prestatario: {l['salary_percentage_borrower']}%)")
            else:
                st.info("Nessun prestito attivo registrato.")

        with tab_storico_scambi:
            st.write("Proposte di scambio ricevute:")
            mie_proposte = [t for t in trades_res if t['receiver_team_id'] == user_team_id and t['status'] == 'In Attesa']
            
            if mie_proposte:
                for tr in mie_proposte:
                    sender_obj = next((t for t in teams if t['id'] == tr['sender_team_id']), None)
                    st.write(f"Proposta da parte di **{sender_obj['name'] if sender_obj else 'Altra Squadra'}** | Conguaglio: {tr['cash_adjustment']}M")
                    
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
with tab6:
    st.header("⚽ Inserimento Risultati Giornata & Convocazioni Under 21")
    st.write("Inserisci i punteggi dei match, spunta i giovani convocati e indica se la formazione è stata caricata in ritardo (scatta la multa automatica).")
    
    if not teams:
        st.warning("Crea prima delle squadre.")
    else:
        with st.form("match_and_u21_form"):
            giornata = st.number_input("Numero Giornata", min_value=1, max_value=38, step=1, value=1)
            
            col_m1, col_m2 = st.columns(2)
            
            team_casa_id = col_m1.selectbox("Squadra Casa", options=[t['id'] for t in teams], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x), key="ins_casa")
            score_casa = col_m1.number_input("Punteggio Totale Casa (es. 74.5)", value=66.0, step=0.5, key="score_c")
            ritardo_casa = col_m1.checkbox("⚠️ Formazione caricata in ritardo? (Multa automatica)", key="rit_c")
            
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
            ritardo_fuori = col_m2.checkbox("⚠️ Formazione caricata in ritardo? (Multa automatica)", key="rit_f")
            
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
                    pts_casa = 3 if score_casa > score_fuori else (1 if score_casa == score_fuori else 0)
                    pts_fuori = 3 if score_fuori > score_casa else (1 if score_fuori == score_casa else 0)
                    if score_casa == score_fuori:
                        pts_fuori = 1
                        
                    supabase.table("match_results").insert([
                        {
                            "matchday": giornata,
                            "team_id": team_casa_id,
                            "opponent_team_id": team_fuori_id,
                            "team_score": score_casa,
                            "opponent_score": score_fuori,
                            "match_points": pts_casa,
                            "u21_convocati": ", ".join(convocati_casa_nomi),
                            "season": active_season
                        },
                        {
                            "matchday": giornata,
                            "team_id": team_fuori_id,
                            "opponent_team_id": team_casa_id,
                            "team_score": score_fuori,
                            "opponent_score": score_casa,
                            "match_points": pts_fuori,
                            "u21_convocati": ", ".join(convocati_fuori_nomi),
                            "season": active_season
                        }
                    ]).execute()
                    
                    multa_valore = 5.0
                    if ritardo_casa:
                        team_c_obj = next(t for t in teams if t['id'] == team_casa_id)
                        nuova_cassa_c = float(team_c_obj['balance']) - multa_valore
                        supabase.table("teams").update({"balance": nuova_cassa_c}).eq("id", team_casa_id).execute()
                        supabase.table("line_up_delays").insert({"team_id": team_casa_id, "matchday": giornata, "fine_amount": multa_valore, "season": active_season}).execute()
                        registra_snapshot_finanziario(team_casa_id, f"Multa Ritardo G. {giornata}", nuova_cassa_c)
                        
                    if ritardo_fuori:
                        team_f_obj = next(t for t in teams if t['id'] == team_fuori_id)
                        nuova_cassa_f = float(team_f_obj['balance']) - multa_valore
                        supabase.table("teams").update({"balance": nuova_cassa_f}).eq("id", team_fuori_id).execute()
                        supabase.table("line_up_delays").insert({"team_id": team_fuori_id, "matchday": giornata, "fine_amount": multa_valore, "season": active_season}).execute()
                        registra_snapshot_finanziario(team_fuori_id, f"Multa Ritardo G. {giornata}", nuova_cassa_f)
                    
                    for uid in convocati_casa_ids:
                        giovane_obj = next((x for x in u21_players if x['id'] == uid), None)
                        if giovane_obj:
                            nuove_presenze = int(giovane_obj.get('presenze', 0)) + 1
                            supabase.table("u21_players").update({"presenze": nuove_presenze}).eq("id", uid).execute()
                            
                    for uid in convocati_fuori_ids:
                        giovane_obj = next((x for x in u21_players if x['id'] == uid), None)
                        if giovane_obj:
                            nuove_presenze = int(giovane_obj.get('presenze', 0)) + 1
                            supabase.table("u21_players").update({"presenze": nuove_presenze}).eq("id", uid).execute()

                    st.success(f"✅ Risultato Giornata {giornata} registrato! Applicate eventuali multe per ritardo e aggiornate le presenze U21.")
                    st.rerun()

# TAB 7: MERCATO (Se Admin)
if st.session_state.is_admin:
    with tab7:
        st.header("Mercato Svincolati & Scadenze di Febbraio (Admin)")
        
        tab_mercato_normale, tab_aste_febbraio = st.tabs(["Listone Svincolati", "🔥 Aste Contratti in Scadenza (Febbraio)"])
        
        with tab_mercato_normale:
            svincolati = [p for p in players if p.get('team_id') is None]
            
            if not svincolati:
                st.warning("⚠️ Il listone è vuoto!")
            elif teams:
                with st.form("acquisto_svincolato_admin"):
                    col1, col2 = st.columns(2)
                    with col1:
                        team_id = st.selectbox("Acquirente", options=[t['id'] for t in teams], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x))
                        
                        svincolati_ordinati = sorted(svincolati, key=lambda x: x['name'])
                        selected_player_id = st.selectbox(
                            "Cerca e Seleziona Giocatore dal Listone", 
                            options=[p['id'] for p in svincolati_ordinati], 
                            format_func=lambda x: next(f"{p['name']} | Ruolo: {p.get('roles', 'N/D')} | Squadra: {p.get('serie_a_team', 'N/D')} | Quotazione: {p.get('current_fg_value', 1)}M" for p in svincolati_ordinati if p['id'] == x)
                        )
                        
                    with col2:
                        player_obj_preview = next((p for p in svincolati if p['id'] == selected_player_id), None)
                        stipendio_fisso = int(player_obj_preview.get('current_fg_value', 1)) if player_obj_preview else 1
                        
                        st.write(f"💵 **Stipendio (Quotazione):** {stipendio_fisso} M")
                        anni_contratto = st.number_input("Anni di Contratto", min_value=1, max_value=3, step=1)
                        
                    if st.form_submit_button("Firma Contratto ✍️"):
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
                            stipendio = stipendio_fisso
                            bonus_firma = calcola_10_percento(stipendio)
                            t_data = next(t for t in teams if t['id'] == team_id)
                            
                            if t_data['balance'] < bonus_firma:
                                st.error("❌ Fondi insufficienti per il bonus firma!")
                            elif (t_data['total_contract_years'] + anni_contratto) > int(rules['max_contract_years']):
                                st.error(f"❌ Limite di {rules['max_contract_years']} anni di contratto superato!")
                            else:
                                supabase.table("players").update({
                                    "team_id": team_id,
                                    "salary": stipendio,
                                    "contract_years": anni_contratto,
                                    "purchase_price": stipendio,
                                    "initial_contract_years": anni_contratto
                                }).eq("id", selected_player_id).execute()
                                
                                new_balance = t_data['balance'] - bonus_firma
                                supabase.table("teams").update({
                                    "balance": new_balance,
                                    "total_contract_years": t_data['total_contract_years'] + anni_contratto
                                }).eq("id", team_id).execute()
                                
                                registra_snapshot_finanziario(team_id, f"Acquisto {nome_giocatore}", new_balance)
                                st.success(f"✅ {nome_giocatore} acquistato con successo!")
                                st.rerun()

        with tab_aste_febbraio:
            st.write("🔥 Gestione giocatori in scadenza dal 1° febbraio con asta al rialzo basata sullo stipendio.")
            scadenti = [p for p in players if p.get('contract_years') == 1 and p.get('team_id') is not None]
            if scadenti:
                for s in scadenti:
                    t_prop = next((t['name'] for t in teams if t['id'] == s['team_id']), "Altra Squadra")
                    st.markdown(f"- **{s['name']}** (Proprietario: {t_prop} | Stipendio attuale: {s.get('salary', 0)}M)")
            else:
                st.info("Nessun giocatore in scadenza di contratto al momento.")

# TAB 8: ADMIN (Esclusivo Admin)
if st.session_state.is_admin:
    with tab8:
        st.header("⚙️ Pannello di Controllo Amministratore")
        
        with st.expander("🛠️ 0. Regole & Parametri della Lega (Gestione Stagioni / Non Retroattivo)"):
            with st.form("edit_league_rules_form"):
                st.write("Modifica i parametri del regolamento per una specifica stagione senza alterare lo storico:")
                
                target_season = st.text_input("Stagione di Riferimento", value=active_season)
                
                r_tranche = st.number_input("Valore Tranche Trimestrale (M)", value=float(rules['tranche_value']), step=1.0)
                r_cap = st.number_input("Tetto Monte Ingaggi / Salary Cap (M)", value=float(rules['salary_cap']), step=1.0)
                r_max_contr = st.number_input("Limite Massimo Anni Contratto per Squadra", value=int(rules['max_contract_years']), step=1)
                
                st.markdown("---")
                st.write("**Bonus Stadio per Livello:**")
                r_b_base = st.number_input("Bonus Stadio - Base", value=float(rules['bonus_base']), step=1.0)
                r_b_med = st.number_input("Bonus Stadio - Medio", value=float(rules['bonus_medio']), step=1.0)
                r_b_top = st.number_input("Bonus Stadio - Top", value=float(rules['bonus_top']), step=1.0)
                r_b_adv = st.number_input("Bonus Stadio - Advanced", value=float(rules['bonus_advanced']), step=1.0)

                st.markdown("---")
                st.write("**Costi di Manutenzione Stadio per Livello:**")
                r_m_base = st.number_input("Manutenzione Stadio - Base", value=float(rules.get('maint_base', 2)), step=1.0)
                r_m_med = st.number_input("Manutenzione Stadio - Medio", value=float(rules.get('maint_medio', 5)), step=1.0)
                r_m_top = st.number_input("Manutenzione Stadio - Top", value=float(rules.get('maint_top', 10)), step=1.0)
                r_m_adv = st.number_input("Manutenzione Stadio - Advanced", value=float(rules.get('maint_advanced', 15)), step=1.0)
                
                st.markdown("---")
                st.write("**Paracaduti Economici (Ultimi tre in classifica):**")
                r_p1 = st.number_input("Paracadute Ultimo (Rank Peggiore)", value=float(rules['paracadute_1']), step=1.0)
                r_p2 = st.number_input("Paracadute Penultimo", value=float(rules['paracadute_2']), step=1.0)
                r_p3 = st.number_input("Paracadute Terzultimo", value=float(rules['paracadute_3']), step=1.0)
                
                if st.form_submit_button("Salva Regole per questa Stagione 💾"):
                    existing_season = supabase.table("league_rules").select("*").eq("season", target_season).execute()
                    
                    rule_payload = {
                        "season": target_season,
                        "tranche_value": r_tranche,
                        "salary_cap": r_cap,
                        "max_contract_years": int(r_max_contr),
                        "bonus_base": r_b_base,
                        "bonus_medio": r_b_med,
                        "bonus_top": r_b_top,
                        "bonus_advanced": r_b_adv,
                        "maint_base": r_m_base,
                        "maint_medio": r_m_med,
                        "maint_top": r_m_top,
                        "maint_advanced": r_m_adv,
                        "paracadute_1": r_p1,
                        "paracadute_2": r_p2,
                        "paracadute_3": r_p3
                    }
                    
                    if existing_season.data:
                        supabase.table("league_rules").update(rule_payload).eq("season", target_season).execute()
                    else:
                        supabase.table("league_rules").insert(rule_payload).execute()
                        
                    st.success(f"✅ Regole salvate per la stagione {target_season} in modo non retroattivo!")
                    st.rerun()

        with st.expander("💰 1. Modifica Manuale Crediti, Anni & Tranches Trimestrali"):
            if teams:
                with st.form("edit_team_balance"):
                    team_to_edit_id = st.selectbox("Seleziona Squadra", options=[t['id'] for t in teams], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x), key="select_edit_team")
                    selected_team = next(t for t in teams if t['id'] == team_to_edit_id)
                    
                    nuovo_saldo = st.number_input("Nuovo Saldo Cassa (M)", value=float(selected_team['balance']), step=1.0)
                    nuovi_anni_contratto = st.number_input("Nuovi Anni Contratto Totali", value=int(selected_team['total_contract_years']), min_value=0, max_value=int(rules['max_contract_years']), step=1)
                    
                    if st.form_submit_button("Aggiorna Bilancio Squadra 💾"):
                        supabase.table("teams").update({
                            "balance": nuovo_saldo,
                            "total_contract_years": nuovi_anni_contratto
                        }).eq("id", team_to_edit_id).execute()
                        registra_snapshot_finanziario(team_to_edit_id, "Modifica Manuale Admin", nuovo_saldo)
                        st.success(f"Dati di {selected_team['name']} aggiornati con successo!")
                        st.rerun()
                
                st.markdown("---")
                st.write(f"🚀 **Erogazione Tranche Trimestrale ({rules['tranche_value']}M)**")
                st.write(f"Distribuisci automaticamente {rules['tranche_value']} crediti a tutte le squadre in base alle regole attive:")
                if st.button(f"Eroga Tranche di {rules['tranche_value']}M a Tutti 💵"):
                    for t in teams:
                        nuova_cassa_tranche = float(t['balance']) + float(rules['tranche_value'])
                        supabase.table("teams").update({"balance": nuova_cassa_tranche}).eq("id", t['id']).execute()
                        registra_snapshot_finanziario(t['id'], "Tranche Trimestrale", nuova_cassa_tranche)
                    st.success(f"✅ Tranche di {rules['tranche_value']}M accreditata a tutte le squadre con successo!")
                    st.rerun()

        with st.expander("🛡️ 2. Gestione Squadre (Credenziali / Elimina Squadra)"):
            if teams:
                with st.form("manage_existing_teams_form"):
                    target_team_id = st.selectbox("Seleziona Squadra da Gestire", options=[t['id'] for t in teams], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x), key="select_target_team_admin")
                    target_team = next(t for t in teams if t['id'] == target_team_id)
                    
                    new_u = st.text_input("Username", value=target_team.get('username') or "")
                    new_p = st.text_input("Password", value=target_team.get('password') or "")
                    
                    col_btn1, col_btn2 = st.columns(2)
                    update_creds = col_btn1.form_submit_button("Aggiorna Credenziali 🔑")
                    delete_team = col_btn2.form_submit_button("Elimina Squadra 🗑️", type="primary")
                    
                    if update_creds:
                        supabase.table("teams").update({
                            "username": new_u,
                            "password": new_p
                        }).eq("id", target_team_id).execute()
                        st.success(f"Credenziali per {target_team['name']} aggiornate!")
                        st.rerun()
                        
                    if delete_team:
                        supabase.table("players").update({
                            "team_id": None,
                            "salary": None,
                            "contract_years": None
                        }).eq("team_id", target_team_id).execute()
                        
                        supabase.table("teams").delete().eq("id", target_team_id).execute()
                        st.success(f"Squadra {target_team['name']} eliminata e giocatori rimessi nel listone!")
                        st.rerun()

        with st.expander("🏟️ 3. Configurazione Stadi"):
            if teams:
                with st.form("edit_stadium_form"):
                    team_stadium_id = st.selectbox("Seleziona Squadra", options=[t['id'] for t in teams], format_func=lambda x: next(t['name'] for t in teams if t['id'] == x), key="select_stadium_team")
                    current_t = next(t for t in teams if t['id'] == team_stadium_id)
                    
                    nuovo_nome_stadio = st.text_input("Nome Stadio", value=current_t.get('stadium_name', 'Stadio Comunale'))
                    
                    livelli_stadi = ['Base', 'Medio', 'Top', 'Advanced']
                    lvl_attuale = current_t.get('stadium_level', 'Base')
                    idx_lvl = livelli_stadi.index(lvl_attuale) if lvl_attuale in livelli_stadi else 0
                    
                    nuovo_livello = st.selectbox("Livello Stadio", options=livelli_stadi, index=idx_lvl)
                    
                    if st.form_submit_button("Salva Parametri Stadio 🏟️"):
                        supabase.table("teams").update({
                            "stadium_name": nuovo_nome_stadio,
                            "stadium_level": nuovo_livello
                        }).eq("id", team_stadium_id).execute()
                        st.success("Stadio aggiornato!")
                        st.rerun()

        with st.expander("📊 4. Importa / Aggiorna Listone Excel (.xlsx)"):
            uploaded_file = st.file_uploader("Scegli file Excel", type=["xlsx", "xls"])
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
                                    valore = float(str(row[col_valore]).replace(',', '.'))
                                except:
                                    valore = 1.0
                                    
                                existing = supabase.table("players").select("*").ilike("name", name).execute()
                                if existing.data:
                                    supabase.table("players").update({
                                        "roles": roles,
                                        "serie_a_team": s_a,
                                        "current_fg_value": valore
                                    }).eq("id", existing.data[0]['id']).execute()
                                    count_aggiornati += 1
                                else:
                                    supabase.table("players").insert({
                                        "name": name,
                                        "roles": roles,
                                        "serie_a_team": s_a,
                                        "current_fg_value": valore
                                    }).execute()
                                    count_nuovi += 1
                                    
                            status_text.empty()
                            progress_bar.empty()
                            st.success(f"✅ Listone aggiornato! Inseriti {count_nuovi} nuovi, aggiornati {count_aggiornati}.")
                            st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")

        with st.expander("🏁 5. Procedura Automatica di Fine Stagione (Bonus, Manutenzione & Paracaduti)"):
            st.write("Esegui il ricalcolo di fine anno in base alle regole della stagione attiva: accredita i bonus stadio, scala i costi di manutenzione, assegna i paracaduti e gestisci gli stadi.")
            
            name_to_id = {t['name']: t['id'] for t in teams}
            classifica_peggiori = sorted(classifica_ordinata, key=lambda x: (x['pt'], x['tot_score']))
            ultimi_tre_ids = [name_to_id[item['name']] for item in classifica_peggiori[:3] if item['name'] in name_to_id]
            
            with st.form("fine_stagione_form"):
                scelte_stadi = {}
                valori_bonus = {
                    'Base': float(rules['bonus_base']), 
                    'Medio': float(rules['bonus_medio']), 
                    'Top': float(rules['bonus_top']), 
                    'Advanced': float(rules['bonus_advanced'])
                }
                valori_manutenzione = {
                    'Base': float(rules.get('maint_base', 2)), 
                    'Medio': float(rules.get('maint_medio', 5)), 
                    'Top': float(rules.get('maint_top', 10)), 
                    'Advanced': float(rules.get('maint_advanced', 15))
                }
                
                for t in teams:
                    t_id = t['id']
                    t_lvl = t.get('stadium_level', 'Base')
                    bonus_spettante = valori_bonus.get(t_lvl, float(rules['bonus_base']))
                    costo_manutenzione = valori_manutenzione.get(t_lvl, float(rules.get('maint_base', 2)))
                    netto_stadio = bonus_spettante - costo_manutenzione
                    
                    paracadute = 0
                    testo_paracadute = ""
                    if ultimi_tre_ids and t_id == ultimi_tre_ids[0]:
                        paracadute = float(rules['paracadute_1'])
                        testo_paracadute = f" | 🪂 Paracadute Ultimo: **+{paracadute}M**"
                    elif len(ultimi_tre_ids) > 1 and t_id == ultimi_tre_ids[1]:
                        paracadute = float(rules['paracadute_2'])
                        testo_paracadute = f" | 🪂 Paracadute Penultimo: **+{paracadute}M**"
                    elif len(ultimi_tre_ids) > 2 and t_id == ultimi_tre_ids[2]:
                        paracadute = float(rules['paracadute_3'])
                        testo_paracadute = f" | 🪂 Paracadute Terzultimo: **+{paracadute}M**"
                        
                    st.markdown(f"**{t['name']}** (Stadio: *{t.get('stadium_name')}* - **{t_lvl}** | Bonus: +{bonus_spettante}M | Manutenzione: -{costo_manutenzione}M -> **Netto: {netto_stadio:+g}M**{testo_paracadute})")
                    
                    scelta = st.radio(
                        f"Scelta stadio per {t['name']}:",
                        ["Mantieni livello (Invariato)", "Ristruttura / Amplia (+1 Livello)", "Riduci / Nessuna azione (Retrocede di 1 Livello)"],
                        key=f"scelta_stadio_{t['id']}"
                    )
                    scelte_stadi[t['id']] = scelta
                    st.divider()
                
                esegui_fine_stagione = st.form_submit_button("Eroga Saldo Netto Stadi, Paracaduti & Elabora Fine Stagione 🏆")
                
                if esegui_fine_stagione:
                     livelli_ordinati = ['Base', 'Medio', 'Top', 'Advanced']
                     
                     for t in teams:
                         t_id = t['id']
                         t_lvl = t.get('stadium_level', 'Base')
                         bonus_spettante = valori_bonus.get(t_lvl, float(rules['bonus_base']))
                         costo_manutenzione = valori_manutenzione.get(t_lvl, float(rules.get('maint_base', 2)))
                         netto_stadio = bonus_spettante - costo_manutenzione
                         
                         paracadute_qt = 0
                         if ultimi_tre_ids and t_id == ultimi_tre_ids[0]:
                             paracadute_qt = float(rules['paracadute_1'])
                         elif len(ultimi_tre_ids) > 1 and t_id == ultimi_tre_ids[1]:
                             paracadute_qt = float(rules['paracadute_2'])
                         elif len(ultimi_tre_ids) > 2 and t_id == ultimi_tre_ids[2]:
                             paracadute_qt = float(rules['paracadute_3'])
                             
                         totale_accredito = netto_stadio + paracadute_qt
                         nuova_cassa = float(t['balance']) + totale_accredito
                         
                         idx_attuale = livelli_ordinati.index(t_lvl) if t_lvl in livelli_ordinati else 0
                         scelta_utente = scelte_stadi[t_id]
                         
                         nuovo_lvl = t_lvl
                         if "Ristruttura" in scelta_utente:
                             if idx_attuale < len(livelli_ordinati) - 1:
                                 nuovo_lvl = livelli_ordinati[idx_attuale + 1]
                         elif "Riduci" in scelta_utente:
                             if idx_attuale > 0:
                                 nuovo_lvl = livelli_ordinati[idx_attuale - 1]
                         
                         supabase.table("teams").update({
                             "balance": nuova_cassa,
                             "stadium_level": nuovo_lvl
                         }).eq("id", t_id).execute()
                         
                         registra_snapshot_finanziario(t_id, "Fine Stagione (Bonus/Paracaduti)", nuova_cassa)
                         
                     st.success("✅ Procedura di fine stagione completata con successo! Accreditati i saldi netti degli stadi e i paracaduti.")
                     st.rerun()