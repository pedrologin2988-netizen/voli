import os
import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__, template_folder='templates')
CORS(app)

# ============================================================
# DADOS EM MEMÓRIA
# ============================================================
players_db = []
config_db = {
    'num_teams': 4,
    'players_per_team': 6,
    'balance_gender': True,
    'auto_fill': True,
    'default_level': 3
}

# Tenta conectar ao Supabase
supabase = None
try:
    from supabase import create_client, Client
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase conectado!")
    else:
        print("⚠️  Variáveis Supabase não configuradas, usando memória")
except Exception as e:
    print(f"⚠️  Erro ao conectar Supabase: {e}")

# ============================================================
# ROTAS
# ============================================================

@app.route('/')
def index():
    """Servir o frontend da pasta templates"""
    try:
        return render_template('index.html')
    except Exception as e:
        return f"Erro ao carregar index: {e}", 500

@app.route('/api/players', methods=['GET'])
def get_players():
    try:
        if supabase:
            try:
                response = supabase.table('players').select('*').execute()
                return jsonify(response.data), 200
            except:
                pass
        return jsonify(players_db), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/players', methods=['POST'])
def save_players():
    global players_db
    try:
        data = request.json
        if not isinstance(data, list):
            return jsonify({'error': 'Dados devem ser uma lista'}), 400
        
        players_db = data
        
        if supabase:
            try:
                supabase.table('players').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
                if data:
                    clean_data = []
                    for p in data:
                        clean_data.append({
                            'name': p.get('name', ''),
                            'gender': p.get('gender', 'M'),
                            'position': p.get('position', 'Passador'),
                            'level': p.get('level', 3),
                            'confirmed': p.get('confirmed', True),
                            'fake': p.get('fake', False)
                        })
                    supabase.table('players').insert(clean_data).execute()
            except Exception as e:
                print(f"Erro ao salvar no Supabase: {e}")
        
        return jsonify({'success': True, 'message': 'Jogadores salvos!'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    try:
        if supabase:
            try:
                response = supabase.table('config').select('*').eq('id', 1).execute()
                if response.data:
                    c = response.data[0]
                    return jsonify({
                        'numTeams': c.get('num_teams', 4),
                        'playersPerTeam': c.get('players_per_team', 6),
                        'balanceGender': c.get('balance_gender', True),
                        'autoFill': c.get('auto_fill', True),
                        'defaultLevel': c.get('default_level', 3)
                    }), 200
            except:
                pass
        return jsonify(config_db), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config', methods=['POST'])
def save_config():
    global config_db
    try:
        data = request.json
        config_db = {
            'num_teams': data.get('numTeams', 4),
            'players_per_team': data.get('playersPerTeam', 6),
            'balance_gender': data.get('balanceGender', True),
            'auto_fill': data.get('autoFill', True),
            'default_level': data.get('defaultLevel', 3)
        }
        
        if supabase:
            try:
                supabase.table('config').update({
                    'num_teams': config_db['num_teams'],
                    'players_per_team': config_db['players_per_team'],
                    'balance_gender': config_db['balance_gender'],
                    'auto_fill': config_db['auto_fill'],
                    'default_level': config_db['default_level'],
                    'updated_at': datetime.now().isoformat()
                }).eq('id', 1).execute()
            except Exception as e:
                print(f"Erro ao salvar config no Supabase: {e}")
        
        return jsonify({'success': True, 'message': 'Configurações salvas!'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset', methods=['DELETE'])
def reset_data():
    global players_db
    players_db = []
    if supabase:
        try:
            supabase.table('players').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        except:
            pass
    return jsonify({'success': True, 'message': 'Dados resetados!'}), 200

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        players = players_db
        stats = {
            'total': len(players),
            'confirmed': sum(1 for p in players if p.get('confirmed', True)),
            'male': sum(1 for p in players if p.get('gender') == 'M'),
            'female': sum(1 for p in players if p.get('gender') == 'F'),
            'levantadores': sum(1 for p in players if p.get('position') == 'Levantador'),
            'passadores': sum(1 for p in players if p.get('position') == 'Passador'),
            'avg_level': round(sum(p.get('level', 0) for p in players) / len(players), 2) if players else 0
        }
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'players': len(players_db),
        'supabase': 'connected' if supabase else 'memory'
    }), 200

@app.errorhandler(Exception)
def handle_error(e):
    print(f"❌ Erro: {e}")
    return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"🚀 Servidor rodando em http://localhost:{port}")
    print(f"📊 Modo: {'Supabase' if supabase else 'Memória'}")
    app.run(host='0.0.0.0', port=port, debug=True)