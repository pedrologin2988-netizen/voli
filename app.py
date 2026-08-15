import os
import json
import sys
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime

# ============================================================
# CONFIGURAÇÃO INICIAL
# ============================================================
app = Flask(__name__, static_folder='static')
CORS(app)

# ============================================================
# CONEXÃO COM SUPABASE - TRY/EXCEPT PARA EVITAR CRASH
# ============================================================
try:
    from supabase import create_client, Client
    
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️  Variáveis de ambiente não configuradas!")
        print("Usando modo de fallback com dados em memória.")
        supabase = None
    else:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Conectado ao Supabase com sucesso!")
except Exception as e:
    print(f"⚠️  Erro ao conectar ao Supabase: {e}")
    print("Usando modo de fallback com dados em memória.")
    supabase = None

# ============================================================
# FALLBACK: DADOS EM MEMÓRIA (CASO SUPABASE FALHE)
# ============================================================
memory_db = {
    'players': [],
    'config': {
        'num_teams': 4,
        'players_per_team': 6,
        'balance_gender': True,
        'auto_fill': True,
        'default_level': 3
    }
}

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================
def get_players_from_db():
    """Buscar jogadores do Supabase ou memória"""
    if supabase:
        try:
            response = supabase.table('players').select('*').order('created_at', desc=True).execute()
            return response.data
        except Exception as e:
            print(f"Erro ao buscar players: {e}")
            return memory_db['players']
    return memory_db['players']

def save_players_to_db(players_data):
    """Salvar jogadores no Supabase ou memória"""
    if supabase:
        try:
            # Limpar existentes
            supabase.table('players').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            # Inserir novos
            if players_data:
                # Limpar campos que não existem no banco
                clean_data = []
                for player in players_data:
                    clean_player = {
                        'name': player.get('name', ''),
                        'gender': player.get('gender', 'M'),
                        'position': player.get('position', 'Ponteiro'),
                        'level': player.get('level', 3),
                        'confirmed': player.get('confirmed', True),
                        'fake': player.get('fake', False)
                    }
                    clean_data.append(clean_player)
                supabase.table('players').insert(clean_data).execute()
            return True
        except Exception as e:
            print(f"Erro ao salvar players: {e}")
            memory_db['players'] = players_data
            return False
    else:
        memory_db['players'] = players_data
        return True

def get_config_from_db():
    """Buscar configurações"""
    if supabase:
        try:
            response = supabase.table('config').select('*').eq('id', 1).execute()
            if response.data:
                config = response.data[0]
                return {
                    'numTeams': config.get('num_teams', 4),
                    'playersPerTeam': config.get('players_per_team', 6),
                    'balanceGender': config.get('balance_gender', True),
                    'autoFill': config.get('auto_fill', True),
                    'defaultLevel': config.get('default_level', 3)
                }
        except Exception as e:
            print(f"Erro ao buscar config: {e}")
    return memory_db['config']

def save_config_to_db(config_data):
    """Salvar configurações"""
    if supabase:
        try:
            data = {
                'num_teams': config_data.get('numTeams', 4),
                'players_per_team': config_data.get('playersPerTeam', 6),
                'balance_gender': config_data.get('balanceGender', True),
                'auto_fill': config_data.get('autoFill', True),
                'default_level': config_data.get('defaultLevel', 3),
                'updated_at': datetime.now().isoformat()
            }
            supabase.table('config').update(data).eq('id', 1).execute()
            return True
        except Exception as e:
            print(f"Erro ao salvar config: {e}")
            memory_db['config'] = config_data
            return False
    else:
        memory_db['config'] = config_data
        return True

# ============================================================
# ROTAS DA API
# ============================================================

@app.route('/')
def index():
    """Servir o frontend"""
    try:
        return send_from_directory('static', 'index.html')
    except Exception as e:
        return f"Erro ao carregar index: {e}", 500

@app.route('/api/players', methods=['GET'])
def get_players():
    """Buscar todos os jogadores"""
    try:
        players = get_players_from_db()
        return jsonify(players), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/players', methods=['POST'])
def save_players():
    """Salvar jogadores"""
    try:
        players_data = request.json
        
        if not isinstance(players_data, list):
            return jsonify({'error': 'Dados devem ser uma lista'}), 400
        
        success = save_players_to_db(players_data)
        
        if success:
            return jsonify({'success': True, 'message': 'Jogadores salvos com sucesso!'}), 200
        else:
            return jsonify({'success': False, 'message': 'Erro ao salvar jogadores'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    """Buscar configurações"""
    try:
        config = get_config_from_db()
        return jsonify(config), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config', methods=['POST'])
def save_config():
    """Salvar configurações"""
    try:
        config_data = request.json
        success = save_config_to_db(config_data)
        
        if success:
            return jsonify({'success': True, 'message': 'Configurações salvas!'}), 200
        else:
            return jsonify({'success': False, 'message': 'Erro ao salvar configurações'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset', methods=['DELETE'])
def reset_data():
    """Resetar todos os dados"""
    try:
        save_players_to_db([])
        save_config_to_db({
            'numTeams': 4,
            'playersPerTeam': 6,
            'balanceGender': True,
            'autoFill': True,
            'defaultLevel': 3
        })
        return jsonify({'success': True, 'message': 'Dados resetados!'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Buscar estatísticas"""
    try:
        players = get_players_from_db()
        
        stats = {
            'total': len(players),
            'confirmed': sum(1 for p in players if p.get('confirmed', True)),
            'male': sum(1 for p in players if p.get('gender') == 'M'),
            'female': sum(1 for p in players if p.get('gender') == 'F'),
            'levantadores': sum(1 for p in players if p.get('position') == 'Levantador'),
            'ponteiros': sum(1 for p in players if p.get('position') == 'Ponteiro'),
            'opostos': sum(1 for p in players if p.get('position') == 'Oposto'),
            'centrais': sum(1 for p in players if p.get('position') == 'Central'),
            'liberos': sum(1 for p in players if p.get('position') == 'Líbero'),
            'avg_level': round(sum(p.get('level', 0) for p in players) / len(players), 2) if players else 0
        }
        
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Verificar status da API"""
    try:
        status = {
            'status': 'healthy',
            'database': 'connected' if supabase else 'fallback_memory',
            'timestamp': datetime.now().isoformat(),
            'players_count': len(get_players_from_db())
        }
        return jsonify(status), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# ============================================================
# MANIPULADOR DE ERROS GLOBAL
# ============================================================
@app.errorhandler(Exception)
def handle_exception(e):
    """Manipulador global de erros"""
    print(f"Erro: {e}")
    return jsonify({
        'error': str(e),
        'message': 'Ocorreu um erro no servidor'
    }), 500

# ============================================================
# EXECUÇÃO LOCAL
# ============================================================
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"🚀 Servidor rodando em http://localhost:{port}")
    print(f"📊 Modo: {'Supabase' if supabase else 'Memória (fallback)'}")
    app.run(host='0.0.0.0', port=port, debug=True)