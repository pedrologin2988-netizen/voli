import os
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime

# Carregar variáveis de ambiente
load_dotenv()

app = Flask(__name__, static_folder='static')
CORS(app)

# ============================================================
# CONEXÃO COM SUPABASE
# ============================================================
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️  Variáveis de ambiente não configuradas!")
    print("Crie um arquivo .env com:")
    print("SUPABASE_URL=sua_url")
    print("SUPABASE_KEY=sua_key")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================================
# INICIALIZAR TABELAS
# ============================================================
def init_db():
    """Criar tabelas via SQL puro"""
    try:
        # SQL para criar tabelas
        sql = """
        CREATE TABLE IF NOT EXISTS players (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            gender VARCHAR(1) NOT NULL CHECK (gender IN ('M', 'F')),
            position VARCHAR(50) NOT NULL,
            level INTEGER NOT NULL CHECK (level BETWEEN 1 AND 5),
            confirmed BOOLEAN DEFAULT TRUE,
            fake BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS config (
            id INTEGER PRIMARY KEY DEFAULT 1,
            num_teams INTEGER DEFAULT 4,
            players_per_team INTEGER DEFAULT 6,
            balance_gender BOOLEAN DEFAULT TRUE,
            auto_fill BOOLEAN DEFAULT TRUE,
            default_level INTEGER DEFAULT 3,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        INSERT INTO config (id, num_teams, players_per_team, balance_gender, auto_fill, default_level)
        VALUES (1, 4, 6, TRUE, TRUE, 3)
        ON CONFLICT (id) DO NOTHING;
        """
        
        # Executar SQL via Supabase
        supabase.rpc('exec_sql', {'sql': sql}).execute()
        print("✅ Tabelas criadas/verificadas com sucesso!")
    except Exception as e:
        print(f"⚠️  Erro ao criar tabelas: {e}")
        print("As tabelas podem já existir ou você precisa criá-las manualmente no SQL Editor do Supabase.")

# ============================================================
# ROTAS DA API
# ============================================================

@app.route('/')
def index():
    """Servir o frontend"""
    return send_from_directory('static', 'index.html')

@app.route('/api/players', methods=['GET'])
def get_players():
    """Buscar todos os jogadores"""
    try:
        response = supabase.table('players').select('*').order('created_at', desc=True).execute()
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/players', methods=['POST'])
def save_players():
    """Salvar jogadores (substitui todos)"""
    try:
        players_data = request.json
        
        if not isinstance(players_data, list):
            return jsonify({'error': 'Dados devem ser uma lista'}), 400
        
        # Limpar todos os jogadores existentes
        supabase.table('players').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        
        # Inserir novos jogadores
        if players_data:
            # Remover campos que não existem no banco
            for player in players_data:
                if 'id' in player:
                    del player['id']
                if 'created_at' in player:
                    del player['created_at']
                if 'updated_at' in player:
                    del player['updated_at']
                # Garantir campos obrigatórios
                if 'gender' not in player:
                    player['gender'] = 'M'
                if 'position' not in player:
                    player['position'] = 'Ponteiro'
                if 'level' not in player:
                    player['level'] = 3
                if 'confirmed' not in player:
                    player['confirmed'] = True
                if 'fake' not in player:
                    player['fake'] = False
            
            response = supabase.table('players').insert(players_data).execute()
        
        return jsonify({'success': True, 'message': 'Jogadores salvos com sucesso!'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    """Buscar configurações"""
    try:
        response = supabase.table('config').select('*').eq('id', 1).execute()
        if response.data:
            config = response.data[0]
            return jsonify({
                'numTeams': config.get('num_teams', 4),
                'playersPerTeam': config.get('players_per_team', 6),
                'balanceGender': config.get('balance_gender', True),
                'autoFill': config.get('auto_fill', True),
                'defaultLevel': config.get('default_level', 3)
            }), 200
        else:
            return jsonify({
                'numTeams': 4,
                'playersPerTeam': 6,
                'balanceGender': True,
                'autoFill': True,
                'defaultLevel': 3
            }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config', methods=['POST'])
def save_config():
    """Salvar configurações"""
    try:
        config_data = request.json
        
        data = {
            'num_teams': config_data.get('numTeams', 4),
            'players_per_team': config_data.get('playersPerTeam', 6),
            'balance_gender': config_data.get('balanceGender', True),
            'auto_fill': config_data.get('autoFill', True),
            'default_level': config_data.get('defaultLevel', 3),
            'updated_at': datetime.now().isoformat()
        }
        
        # Atualizar ou inserir
        response = supabase.table('config').update(data).eq('id', 1).execute()
        
        return jsonify({'success': True, 'message': 'Configurações salvas!'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset', methods=['DELETE'])
def reset_data():
    """Resetar todos os dados"""
    try:
        # Deletar todos os jogadores
        supabase.table('players').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        
        # Resetar configurações
        supabase.table('config').update({
            'num_teams': 4,
            'players_per_team': 6,
            'balance_gender': True,
            'auto_fill': True,
            'default_level': 3,
            'updated_at': datetime.now().isoformat()
        }).eq('id', 1).execute()
        
        return jsonify({'success': True, 'message': 'Dados resetados!'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Buscar estatísticas"""
    try:
        # Buscar todos os jogadores
        response = supabase.table('players').select('*').execute()
        players = response.data
        
        # Calcular estatísticas manualmente
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
        # Testar conexão com Supabase
        response = supabase.table('config').select('*').limit(1).execute()
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }), 500

# ============================================================
# INICIALIZAÇÃO
# ============================================================
if __name__ == '__main__':
    # Inicializar banco de dados
    init_db()
    
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)